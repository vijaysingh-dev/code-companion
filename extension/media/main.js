// Webview entry point. The UI structure is in index.html; this grabs the named
// elements, hands them to the component controllers, bridges their events to/from
// the extension host over postMessage, and toggles between the home (session list)
// and chat views. The composer is shared: sending from the home view starts a new
// chat; the ← back button returns to the list.

import { createContextBar } from "./components/contextBar.js";
import { createToolbar } from "./components/toolbar.js";
import { createMessages } from "./components/messages.js";
import { createComposer } from "./components/composer.js";
import { createHome } from "./components/home.js";

const vscode = acquireVsCodeApi();
const post = (message) => vscode.postMessage(message);
const $ = (id) => document.getElementById(id);

const banner = $("banner");
const brand = $("brand"); // shows "Code Companion" on home, the chat title on chat
let currentSessionId = null;

// Inline title editing (top bar).
const titleInput = $("title-input");
const titleEditBtn = $("title-edit");
const titleSaveBtn = $("title-save");
const titleCancelBtn = $("title-cancel");
let editingTitle = false;

const messages = createMessages({ root: $("messages"), empty: $("empty") });
const toolbar = createToolbar({ modelEl: $("dd-model"), effortEl: $("dd-effort"), modeEl: $("dd-mode"), status: $("status") });
const home = createHome({
  list: $("session-list"),
  empty: $("home-empty"),
  onOpen: (id) => post({ type: "openSession", id }),
  onRename: (id, title) => post({ type: "renameSession", id, title }),
  onDelete: (id) => post({ type: "deleteSession", id }),
});
const contextBar = createContextBar({
  root: $("context"),
  pills: $("context-pills"),
  onAddActive: () => post({ type: "addActiveFile" }),
  onPick: () => post({ type: "pickFiles" }),
  onRemove: (fsPath) => post({ type: "removeContext", fsPath }),
});
const composer = createComposer({
  input: $("input"),
  button: $("send"),
  onSend: send,
  onStop: () => post({ type: "stop" }),
});

$("login-btn").addEventListener("click", () => post({ type: "login" }));
$("back").addEventListener("click", () => post({ type: "goHome" }));

titleEditBtn.addEventListener("click", enterTitleEdit);
titleCancelBtn.addEventListener("click", exitTitleEdit);
titleSaveBtn.addEventListener("click", commitTitle);
titleInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    commitTitle();
  } else if (e.key === "Escape") {
    e.preventDefault();
    exitTitleEdit();
  }
});

function setView(view) {
  document.body.classList.toggle("view-home", view === "home");
  document.body.classList.toggle("view-chat", view === "chat");
  exitTitleEdit(); // leaving/entering a view cancels any in-progress rename
}

// Return to the home list. Driven by the host ("home" message) so the ← back
// button and the native History command behave identically.
function showHome() {
  currentSessionId = null;
  messages.clear();
  brand.textContent = "Code Companion";
  brand.title = "Code Companion";
  setView("home");
}

function setChatTitle(title) {
  brand.textContent = title || "New Chat";
  brand.title = title || "New Chat";
}

// ── Title editing ────────────────────────────────────────────────────────────
function enterTitleEdit() {
  if (!currentSessionId) {
    return;
  }
  editingTitle = true;
  titleInput.value = brand.textContent;
  updateTitleControls();
  titleInput.focus();
  titleInput.select();
}

function exitTitleEdit() {
  editingTitle = false;
  updateTitleControls();
}

function commitTitle() {
  const next = titleInput.value.trim();
  if (next && currentSessionId && next !== brand.textContent) {
    post({ type: "renameSession", id: currentSessionId, title: next });
    setChatTitle(next); // optimistic; host confirms via a "title" message
  }
  exitTitleEdit();
}

// ✎ shows only in chat view with a saved session; ✓/✕ + input show while editing.
function updateTitleControls() {
  const canEdit = document.body.classList.contains("view-chat") && Boolean(currentSessionId);
  brand.hidden = editingTitle;
  titleInput.hidden = !editingTitle;
  titleEditBtn.hidden = editingTitle || !canEdit;
  titleSaveBtn.hidden = !editingTitle;
  titleCancelBtn.hidden = !editingTitle;
}

function setAuthenticated(authenticated) {
  document.body.classList.toggle("signed-out", !authenticated);
  if (authenticated) {
    composer.focus();
  }
}

function send(text) {
  const selection = toolbar.getSelection();
  if (!selection.model) {
    setBanner("No model available — check the backend and your settings.");
    return;
  }
  setView("chat"); // sending from the home view opens the new chat
  messages.addUser(text);
  composer.setStreaming(true);
  post({ type: "send", text, ...selection });
}

function setBanner(text) {
  banner.textContent = text ?? "";
}

window.addEventListener("message", (e) => {
  const msg = e.data;
  switch (msg.type) {
    case "init":
      toolbar.setModels(msg.models);
      contextBar.render(msg.context);
      setBanner(msg.error ?? "");
      setAuthenticated(msg.authenticated);
      break;
    case "auth":
      setAuthenticated(msg.authenticated);
      break;
    case "models":
      toolbar.setModels(msg.models);
      break;
    case "health":
      toolbar.setHealth(msg.status);
      break;
    case "context":
      contextBar.render(msg.files);
      break;
    case "activeFile":
      contextBar.setCanAddActive(msg.canAdd);
      break;
    case "sessions":
      home.render(msg.sessions);
      break;
    case "home":
      showHome();
      break;
    case "sessionOpened":
      currentSessionId = msg.session.id;
      messages.load(msg.session.messages);
      contextBar.render([]);
      toolbar.select(msg.session.provider, msg.session.model);
      setChatTitle(msg.session.title);
      composer.setStreaming(false);
      setView("chat");
      break;
    case "title":
      // Only the open chat's title drives the top bar; a home-row rename just
      // refreshes the list (handled by the following "sessions" message).
      if (document.body.classList.contains("view-chat")) {
        currentSessionId = msg.id; // adopt the id for a freshly created session's first title
        setChatTitle(msg.title);
        updateTitleControls();
      }
      break;
    case "stream":
      messages.streamEvent(msg.event);
      break;
    case "turnEnd":
      messages.turnEnd();
      composer.setStreaming(false);
      break;
    case "cleared":
      currentSessionId = null;
      messages.clear();
      contextBar.render([]);
      composer.setStreaming(false);
      setChatTitle(null);
      setBanner("");
      setView("chat");
      break;
    case "error":
      messages.addError(msg.message);
      composer.setStreaming(false);
      break;
  }
});

updateTitleControls();
post({ type: "ready" });
