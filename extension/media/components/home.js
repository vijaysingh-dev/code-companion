// Home view: the list of past chats. Each row clones #tpl-session and shows the
// title + a relative "created" time. Clicking opens it; the row also carries an
// inline rename (✎ → input + ✓/✕) and a delete (🗑) action.

export function createHome({ list, empty, onOpen, onRename, onDelete }) {
  const template = document.getElementById("tpl-session");

  function render(sessions) {
    list.replaceChildren();
    empty.classList.toggle("hidden", sessions.length > 0);
    for (const session of sessions) {
      list.appendChild(row(session));
    }
  }

  function row(session) {
    const node = template.content.firstElementChild.cloneNode(true);
    const open = node.querySelector(".cc-session-open");
    const titleEl = node.querySelector(".cc-session-title");
    const input = node.querySelector(".cc-session-input");
    const rename = node.querySelector(".cc-session-rename");
    const del = node.querySelector(".cc-session-delete");
    const save = node.querySelector(".cc-session-save");
    const cancel = node.querySelector(".cc-session-cancel");

    const label = session.title || "Untitled chat";
    open.title = label;
    titleEl.textContent = label;
    node.querySelector(".cc-session-time").textContent = relativeTime(session.created_at);

    open.addEventListener("click", () => onOpen(session.id));
    del.addEventListener("click", () => onDelete(session.id));
    rename.addEventListener("click", enter);
    cancel.addEventListener("click", exit);
    save.addEventListener("click", commit);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        commit();
      } else if (e.key === "Escape") {
        e.preventDefault();
        exit();
      }
    });

    function enter() {
      input.value = titleEl.textContent;
      node.classList.add("editing");
      toggle(true);
      input.focus();
      input.select();
    }

    function exit() {
      node.classList.remove("editing");
      toggle(false);
    }

    function commit() {
      const next = input.value.trim();
      if (next && next !== titleEl.textContent) {
        onRename(session.id, next); // host renames + refreshes the list
      }
      exit();
    }

    function toggle(editing) {
      input.hidden = !editing;
      save.hidden = !editing;
      cancel.hidden = !editing;
      rename.hidden = editing;
      del.hidden = editing;
    }

    return node;
  }

  return { render };
}

// "just now" → minutes → hours → days → months → "Mon YYYY" past a year.
function relativeTime(iso) {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) {
    return "";
  }
  const minutes = Math.floor((Date.now() - then) / 60_000);
  if (minutes < 1) {
    return "just now";
  }
  if (minutes < 60) {
    return `${minutes}m ago`;
  }
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours}h ago`;
  }
  const days = Math.floor(hours / 24);
  if (days < 30) {
    return `${days}d ago`;
  }
  const months = Math.floor(days / 30);
  if (months < 12) {
    return `${months}mo ago`;
  }
  return new Date(then).toLocaleDateString(undefined, { month: "short", year: "numeric" });
}
