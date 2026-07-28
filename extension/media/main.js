// Webview entry point. The UI structure is in index.html; this grabs the named
// elements, hands them to the component controllers, and bridges their events
// to/from the extension host over postMessage.

import { createContextBar } from "./components/contextBar.js";
import { createToolbar } from "./components/toolbar.js";
import { createMessages } from "./components/messages.js";
import { createComposer } from "./components/composer.js";

const vscode = acquireVsCodeApi();
const post = (message) => vscode.postMessage(message);
const $ = (id) => document.getElementById(id);

const banner = $("banner");

const messages = createMessages({ root: $("messages"), empty: $("empty") });
const toolbar = createToolbar({ mode: $("mode"), model: $("model"), effort: $("effort"), status: $("status") });
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
$("expand").addEventListener("click", () => post({ type: "expand" }));

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
    case "stream":
      messages.streamEvent(msg.event);
      break;
    case "turnEnd":
      composer.setStreaming(false);
      break;
    case "cleared":
      messages.clear();
      contextBar.render([]);
      composer.setStreaming(false);
      setBanner("");
      break;
    case "error":
      messages.addError(msg.message);
      composer.setStreaming(false);
      break;
  }
});

post({ type: "ready" });
