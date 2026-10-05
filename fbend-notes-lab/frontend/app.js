const API = (window.API_BASE_URL || "").replace(/\/$/, "");

const statusEl = document.getElementById("status");
const listEl = document.getElementById("notes");
const emptyEl = document.getElementById("empty");
const form = document.getElementById("note-form");
const input = document.getElementById("note-text");
document.getElementById("api-url").textContent = API || "(not set - edit config.js)";

function showError(msg) {
  statusEl.className = "status error";
  statusEl.innerHTML =
    `<b>Cannot reach backend.</b> ${msg}<br>` +
    `<small>Check: 1) URL in config.js  2) App Service is running  3) CORS in App Service allows this site. ` +
    `Open DevTools (F12) &rarr; Console for details.</small>`;
}

async function checkHealth() {
  try {
    const res = await fetch(`${API}/api/health`);
    const h = await res.json();
    const color = h.storage === "cosmos" ? "ok" : "warn";
    statusEl.className = `status ${color}`;
    statusEl.innerHTML =
      `Backend <b>connected</b> &middot; site: <b>${h.site}</b> &middot; storage: <b>${h.storage}</b>` +
      (h.storage === "memory" ? " <small>(notes disappear when the app restarts)</small>" : "") +
      (h.storageError ? `<br><small>${h.storageError}</small>` : "");
    return true;
  } catch (e) {
    showError(e.message);
    return false;
  }
}

async function loadNotes() {
  const res = await fetch(`${API}/api/notes`);
  const notes = await res.json();
  listEl.innerHTML = "";
  emptyEl.style.display = notes.length ? "none" : "block";
  for (const n of notes) {
    const li = document.createElement("li");
    const text = document.createElement("span");
    text.textContent = n.text;
    const time = document.createElement("time");
    time.textContent = new Date(n.createdAt).toLocaleString();
    const del = document.createElement("button");
    del.textContent = "✕";
    del.title = "Delete";
    del.onclick = async () => {
      await fetch(`${API}/api/notes/${n.id}`, { method: "DELETE" });
      loadNotes();
    };
    li.append(text, time, del);
    listEl.appendChild(li);
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  try {
    await fetch(`${API}/api/notes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    input.value = "";
    loadNotes();
  } catch (err) {
    showError(err.message);
  }
});

(async () => {
  if (await checkHealth()) loadNotes();
})();
