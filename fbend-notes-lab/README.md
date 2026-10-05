# FBEND Notes Lab: Frontend + Backend on Azure (Portal only)

A notes app with three parts, each on its own Azure service, all in the resource group **FBEND**.

```
 Browser
    │
    ▼
┌──────────────────────┐   fetch() / JSON   ┌──────────────────────┐   SDK   ┌──────────────────────┐
│ Azure Static Web Apps│ ─────────────────▶ │  Azure App Service   │ ──────▶ │   Azure Cosmos DB    │
│ frontend/            │                    │  backend/ (FastAPI)  │         │   (NoSQL API)        │
│ HTML + CSS + JS      │ ◀───────────────── │  /api/notes          │ ◀────── │   notesdb / notes    │
└──────────────────────┘     CORS check     └──────────────────────┘         └──────────────────────┘
        (from GitHub)                            (from GitHub)                   (keys in env vars)
```

| Folder | What it is | Where it goes |
|---|---|---|
| `frontend/` | `index.html`, `app.js`, `style.css`, `config.js` | GitHub repo → **Static Web App** |
| `backend/` | `main.py` (FastAPI), `requirements.txt` | GitHub repo → **App Service (Linux, Python)** |

**API endpoints:** `GET /api/health`, `GET /api/notes`, `POST /api/notes`, `DELETE /api/notes/{id}`, and interactive docs at `/docs`.

**The backend chooses its storage by itself.** With no Cosmos settings it keeps notes **in memory**. Add `COSMOS_ENDPOINT` + `COSMOS_KEY` and it switches to **Cosmos DB**. The status bar on the page shows which mode is active.

---

## Before class (checklist)

- [ ] Azure subscription with resource group **FBEND** (done ✅)
- [ ] Each learner has a **GitHub account** (free)
- [ ] Learners have this folder unzipped on their laptop
- [ ] Optional (experienced learners): Python 3.10+ for running locally

**Naming convention** (Azure names must be globally unique, so add your initials):

| Resource | Example name |
|---|---|
| App Service | `app-fbend-notes-<initials>` |
| Static Web App | `swa-fbend-notes-<initials>` |
| Cosmos DB account | `cosmos-fbend-<initials>` (lowercase, no underscores) |
| Region | **Central India** (Static Web App: **East Asia**) |

---

## Lab flow (~2.5 hours)

| # | Stage | Azure concept | Time |
|---|---|---|---|
| 0 | Tour the architecture and RG FBEND | Resource groups, regions | 10 min |
| 1 | Put the code on GitHub | Source control as deploy source | 15 min |
| 2 | Deploy the backend to App Service | PaaS, App Service plan, Deployment Center | 30 min |
| 3 | Deploy the frontend to Static Web Apps | Static hosting, CI/CD with GitHub Actions | 20 min |
| 4 | Fix the CORS error | Browser security, App Service CORS | 10 min |
| 5 | Restart the backend and lose the data | Stateless apps, why databases exist | 5 min |
| 6 | Add Cosmos DB | Managed NoSQL, keys, env variables | 30 min |
| 7 | Observe: logs and metrics | Log stream, Metrics | 10 min |
| 8 | Stretch (experienced): Key Vault + Managed Identity | Secrets, identity | 20 min |
| 9 | Clean up | Cost control | 5 min |

---

## Stage 0: Optional local run (for experienced learners)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
Open http://localhost:8000/docs. Then open `frontend/index.html` in a browser (or use VS Code Live Server). `config.js` already points to `http://localhost:8000`.

---

## Stage 1: Put the code on GitHub (no git needed)

Create **two** repositories, one per tier (this mirrors a frontend team and a backend team):

1. github.com → **New repository** → name `fbend-notes-backend` → Public → **Create**.
2. Click **uploading an existing file** → drag in the **files inside** `backend/` (`main.py`, `requirements.txt`) → **Commit changes**.
3. Repeat for `fbend-notes-frontend` with the **files inside** `frontend/` (`index.html`, `app.js`, `style.css`, `config.js`).

> ⚠️ Most common mistake: uploading the *folder*. `main.py` and `index.html` must be at the **root** of each repo.

---

## Stage 2: Backend on Azure App Service

### 2a. Create the Web App
Portal → **Create a resource** → **Web App** → fill in:

| Field | Value |
|---|---|
| Resource Group | **FBEND** |
| Name | `app-fbend-notes-<initials>` |
| Publish | **Code** |
| Runtime stack | **Python 3.12** |
| Operating System | **Linux** |
| Region | **Central India** |
| Pricing plan | **Basic B1** (reliable for class) or **Free F1** (₹0, slower, 60 CPU-min/day) |

→ **Review + create** → **Create** → **Go to resource**.

Explain: the **App Service plan** is the VM you pay for. The **Web App** is your app that runs on it. Several apps can share one plan.

### 2b. Set the startup command
Web App → **Settings → Configuration → General settings** → **Startup Command**:
```
gunicorn --bind=0.0.0.0 --timeout 600 -w 2 -k uvicorn.workers.UvicornWorker main:app
```
→ **Save**.

Explain: FastAPI is an ASGI app, so it runs on gunicorn with uvicorn workers. Without this command, App Service would look for a Flask/Django app.

### 2c. Connect GitHub (Deployment Center)
Web App → **Deployment → Deployment Center**:
- Source: **GitHub** → **Authorize** → pick org / `fbend-notes-backend` / branch `main`
- Authentication type: **User-assigned identity** (default). If you get a permission error, choose **Basic authentication** instead. You may need to turn on *SCM Basic Auth Publishing Credentials* under Configuration → General settings.
- **Save**

This commits a GitHub Actions workflow to your repo. Open the repo → **Actions** tab to watch the build (about 3–5 min).

### 2d. Test it
Open `https://app-fbend-notes-<initials>.azurewebsites.net/docs`. Try **POST /api/notes**, then **GET /api/notes**.
Open `/api/health`. It should show `"storage": "memory"`.

✅ **Checkpoint:** the backend is live on the internet.

---

## Stage 3: Frontend on Azure Static Web Apps

### 3a. Point the frontend at your backend
In GitHub, open `fbend-notes-frontend/config.js` → ✏️ **Edit**:
```js
window.API_BASE_URL = "https://app-fbend-notes-<initials>.azurewebsites.net";
```
(no trailing slash) → **Commit changes**.

### 3b. Create the Static Web App
Portal → **Create a resource** → **Static Web App**:

| Field | Value |
|---|---|
| Resource Group | **FBEND** |
| Name | `swa-fbend-notes-<initials>` |
| Plan type | **Free** |
| Source | **GitHub** → sign in → `fbend-notes-frontend` / `main` |
| Build Presets | **Custom** |
| App location | `/` |
| Api location | *(leave empty)* |
| Output location | *(leave empty)* |

→ **Review + create** → **Create** → **Go to resource** → wait for the GitHub Action to finish (about 2 min) → click the **URL**.

---

## Stage 4: The CORS error (planned failure ✋)

The page loads but shows a red **"Cannot reach backend"**. Press **F12 → Console** and you will see:
`...has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header...`

**Why:** the page comes from `*.azurestaticapps.net` and the API is on `*.azurewebsites.net`. They are different origins, so the browser blocks the call unless the API explicitly allows it.

**Fix (Portal):** Web App → **API → CORS** → Allowed Origins → add your Static Web App URL, e.g.
`https://happy-sea-0abc123.azurestaticapps.net` (no trailing slash) → **Save**. Refresh the page.

✅ **Checkpoint:** the status bar is yellow: *connected · storage: memory*. Add a few notes.

> Note for experienced learners: `main.py` adds CORS middleware only when running locally (`WEBSITE_SITE_NAME` is not set). On Azure, CORS is handled by the platform setting. Don't configure both.

---

## Stage 5: Restart and lose the data (planned failure ✋)

Web App → **Overview → Restart** → refresh the frontend. **All notes are gone.**

**Why:** the notes lived in the app's RAM. App Services restart, scale out to several instances, and move between machines. **Web apps must be stateless.** State belongs in a database. That's next.

---

## Stage 6: Add Azure Cosmos DB

### 6a. Create the account
Portal → **Create a resource** → **Azure Cosmos DB** → **Azure Cosmos DB for NoSQL** → **Create**:

| Field | Value |
|---|---|
| Resource Group | **FBEND** |
| Account Name | `cosmos-fbend-<initials>` |
| Location | **Central India** |
| Capacity mode | **Serverless** (pay per request, best for labs) *or* **Provisioned throughput** + **Apply Free Tier Discount** (only one free-tier account per subscription) |

→ **Review + create** → **Create** (takes about 5 min; explain the concepts while it builds).

Explain: **Account → Database → Container → Items (JSON)**. The **partition key** (`/id` here) decides how data is spread across servers.

### 6b. Create the database and container (Data Explorer)
Cosmos account → **Data Explorer** → **New Container**:
- Database id: **Create new** → `notesdb`
- Container id: `notes`
- Partition key: `/id`
→ **OK**

(The app would also create these automatically, but doing it by hand shows the structure.)

### 6c. Copy the keys
Cosmos account → **Settings → Keys** → copy **URI** and **PRIMARY KEY**.

### 6d. Give them to the backend
Web App → **Settings → Environment variables → App settings → + Add**:

| Name | Value |
|---|---|
| `COSMOS_ENDPOINT` | *(the URI)* |
| `COSMOS_KEY` | *(the PRIMARY KEY)* |
| `COSMOS_DATABASE` | `notesdb` *(optional, this is the default)* |
| `COSMOS_CONTAINER` | `notes` *(optional, this is the default)* |

→ **Apply** → **Confirm** (the app restarts automatically).

Explain: secrets go in **environment variables**, never in code or GitHub.

### 6e. Prove it works
- Refresh the frontend. The status bar turns **green**: *storage: cosmos*.
- Add notes → Cosmos **Data Explorer → notesdb → notes → Items** → see the JSON documents.
- **Restart** the Web App again → the notes are **still there**. 🎉

✅ **Checkpoint:** a full 3-tier app on Azure.

---

## Stage 7: Observe it

- Web App → **Monitoring → Log stream**: watch requests come in live as you click in the UI (enable **App Service logs → Application logging: File System** first if it's empty).
- Web App → **Monitoring → Metrics**: chart *Requests* and *Http 4xx*.
- Cosmos → **Monitoring → Metrics**: *Total Request Units*.
- Optional: Web App → **Application Insights → Turn on** for request traces and failures.

---

## Stage 8: Stretch for experienced learners (Key Vault + Managed Identity)

Remove the raw key from App Settings:

1. Web App → **Settings → Identity → System assigned → On → Save**.
2. Create a **Key Vault** in FBEND (permission model: **Azure role-based access control**).
3. Key Vault → **Access control (IAM) → Add role assignment** → give *yourself* **Key Vault Secrets Officer**, and give the Web App's managed identity **Key Vault Secrets User**.
4. Key Vault → **Objects → Secrets → Generate/Import** → name `cosmos-key`, value = the Cosmos primary key. Copy the **Secret Identifier** URI.
5. Web App → Environment variables → change `COSMOS_KEY` to:
   `@Microsoft.KeyVault(SecretUri=<secret identifier URI>)` → Apply.
6. The setting shows a green ✔ **Key vault Reference**. The app works the same, but the key now lives only in Key Vault.

Discussion: what changes if we rotate the key? What's the next step? (Cosmos data-plane RBAC with no keys at all.)

---

## Stage 9: Clean up 💰

Leaving resources running costs money (B1 plan, Cosmos provisioned throughput).
- Quickest: Portal → **Resource groups → FBEND → Delete resource group** (deletes everything inside, including the group).
- To keep the group: open FBEND, select all resources, and click **Delete**.

---

## Plan B: deploy the backend without GitHub

If GitHub auth is blocked in class, use **Cloud Shell** inside the Portal (the `>_` icon at the top bar):
1. Cloud Shell (Bash) → **Manage files → Upload** → `backend.zip` (provided; it has `main.py` at the root).
2. Run:
   ```bash
   az webapp config appsettings set -g FBEND -n app-fbend-notes-<initials> --settings SCM_DO_BUILD_DURING_DEPLOYMENT=true
   az webapp deploy -g FBEND -n app-fbend-notes-<initials> --src-path backend.zip --type zip
   ```

---

## Troubleshooting

| Symptom | Likely cause → fix |
|---|---|
| `/docs` shows *Application Error* or default page | Startup command missing or wrong (Stage 2b). Check **Log stream**. |
| `ModuleNotFoundError: fastapi` in logs | `requirements.txt` not at repo root, or build skipped → check the GitHub Action log |
| Red "Cannot reach backend" + CORS in console | Stage 4: add the exact SWA URL in **API → CORS**, no trailing slash |
| Red "Cannot reach backend", no CORS message | Wrong URL in `config.js` (typo, `http` vs `https`, trailing slash), or the app is stopped |
| Status says *memory* after adding Cosmos | Env variable names misspelled, or the app hasn't restarted |
| Status shows "Cosmos DB connection failed" | Wrong key/endpoint, or Cosmos networking set to *Selected networks* → allow **All networks** for the lab |
| SWA still shows old `config.js` | Wait for the GitHub Action to finish, then hard-refresh (Ctrl+F5) |
| Deployment Center error about identity / role | Choose **Basic authentication** (Stage 2c) |
| F1 app very slow on first call | Free tier cold start; wait 20–30 s or use B1 |
