"""
FBEND Notes API  -  a tiny FastAPI backend for the Azure lab.

Storage mode is picked automatically:
  * No COSMOS_ENDPOINT / COSMOS_KEY set  -> in-memory list (data is lost on restart)
  * Both set (App Service > Environment variables) -> Azure Cosmos DB (data persists)
"""
import os
import socket
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="FBEND Notes API", version="1.0")

# ---------------------------------------------------------------------------
# CORS
# On your laptop we allow every origin so the local frontend just works.
# On Azure App Service (WEBSITE_SITE_NAME is set automatically) we DON'T add it
# here - you configure it in the Portal: App Service > API > CORS.
# ---------------------------------------------------------------------------
if not os.getenv("WEBSITE_SITE_NAME"):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )


class NoteIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)


# ---------------------------------------------------------------------------
# Storage option 1: in-memory (stage 1 of the lab)
# ---------------------------------------------------------------------------
class MemoryStore:
    mode = "memory"

    def __init__(self):
        self.items: list[dict] = []

    def list(self):
        return sorted(self.items, key=lambda n: n["createdAt"], reverse=True)

    def add(self, note: dict):
        self.items.append(note)
        return note

    def delete(self, note_id: str):
        before = len(self.items)
        self.items = [n for n in self.items if n["id"] != note_id]
        return len(self.items) < before


# ---------------------------------------------------------------------------
# Storage option 2: Azure Cosmos DB for NoSQL (stage 2 of the lab)
# ---------------------------------------------------------------------------
class CosmosStore:
    mode = "cosmos"

    def __init__(self, endpoint: str, key: str):
        from azure.cosmos import CosmosClient, PartitionKey

        db_name = os.getenv("COSMOS_DATABASE", "notesdb")
        container_name = os.getenv("COSMOS_CONTAINER", "notes")
        client = CosmosClient(endpoint, credential=key)
        db = client.create_database_if_not_exists(id=db_name)
        self.container = db.create_container_if_not_exists(
            id=container_name, partition_key=PartitionKey(path="/id")
        )

    def list(self):
        query = "SELECT c.id, c.text, c.createdAt FROM c ORDER BY c.createdAt DESC"
        return list(self.container.query_items(query, enable_cross_partition_query=True))

    def add(self, note: dict):
        self.container.create_item(note)
        return note

    def delete(self, note_id: str):
        from azure.cosmos.exceptions import CosmosResourceNotFoundError

        try:
            self.container.delete_item(item=note_id, partition_key=note_id)
            return True
        except CosmosResourceNotFoundError:
            return False


def build_store():
    endpoint, key = os.getenv("COSMOS_ENDPOINT"), os.getenv("COSMOS_KEY")
    if endpoint and key:
        try:
            return CosmosStore(endpoint, key), None
        except Exception as exc:  # show the problem instead of crashing the app
            return MemoryStore(), f"Cosmos DB connection failed, using memory: {exc}"
    return MemoryStore(), None


store, store_error = build_store()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    return {"message": "FBEND Notes API is running. Open /docs to try it."}


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "storage": store.mode,
        "storageError": store_error,
        "servedBy": os.getenv("WEBSITE_INSTANCE_ID", socket.gethostname())[:12],
        "site": os.getenv("WEBSITE_SITE_NAME", "local"),
        "time": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/notes")
def list_notes():
    return store.list()


@app.post("/api/notes", status_code=201)
def add_note(body: NoteIn):
    note = {
        "id": str(uuid.uuid4()),
        "text": body.text.strip(),
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    return store.add(note)


@app.delete("/api/notes/{note_id}", status_code=204)
def delete_note(note_id: str):
    if not store.delete(note_id):
        raise HTTPException(status_code=404, detail="Note not found")
