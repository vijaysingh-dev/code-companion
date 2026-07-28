// Transcript renderer. Clones the #tpl-* templates from index.html and folds
// streamed StreamEvents into the current assistant turn. Content blocks are
// keyed by their stream `index` so interleaved text / thinking / tool calls
// stay ordered.

export function createMessages({ root, empty }) {
  let current = null; // { body, blocks: Map<index, {node, buf}> }

  const clone = (id) => document.getElementById(id).content.firstElementChild.cloneNode(true);

  function addUser(text) {
    empty.remove();
    const node = clone("tpl-user");
    node.querySelector(".cc-msg-body").textContent = text;
    root.appendChild(node);
    scroll();
  }

  function ensureTurn() {
    if (current) {
      return current;
    }
    empty.remove();
    const node = clone("tpl-assistant");
    root.appendChild(node);
    current = { body: node.querySelector(".cc-body"), blocks: new Map() };
    return current;
  }

  function block(turn, index, templateId) {
    let entry = turn.blocks.get(index);
    if (!entry) {
      entry = { node: clone(templateId), buf: "" };
      turn.blocks.set(index, entry);
      turn.body.appendChild(entry.node);
    }
    return entry;
  }

  function streamEvent(event) {
    const i = event.index ?? 0;
    switch (event.type) {
      case "message_start":
        ensureTurn();
        break;
      case "text_delta": {
        const entry = block(ensureTurn(), i, "tpl-text");
        entry.buf += event.text ?? "";
        entry.node.textContent = entry.buf;
        break;
      }
      case "thinking_delta": {
        const entry = block(ensureTurn(), i, "tpl-thinking");
        entry.buf += event.text ?? "";
        entry.node.textContent = entry.buf;
        break;
      }
      case "tool_use_start": {
        const entry = block(ensureTurn(), i, "tpl-tool");
        entry.node.querySelector(".cc-tool-name").textContent = event.tool_name ?? "tool";
        break;
      }
      case "tool_use_delta": {
        const entry = current && current.blocks.get(i);
        if (entry) {
          entry.buf += event.tool_args_delta ?? "";
          entry.node.querySelector(".cc-tool-args").textContent = ` ${entry.buf}`;
        }
        break;
      }
      case "error":
        addError(event.error ?? "Unknown error");
        break;
      // stop / usage / tool_use_stop / done: nothing to render.
    }
    scroll();
  }

  function turnEnd() {
    current = null;
  }

  function addError(text) {
    empty.remove();
    const node = clone("tpl-error");
    node.querySelector(".cc-error").textContent = text;
    root.appendChild(node);
    scroll();
  }

  function clear() {
    current = null;
    root.replaceChildren(empty);
  }

  function scroll() {
    root.scrollTop = root.scrollHeight;
  }

  return { addUser, streamEvent, turnEnd, addError, clear };
}
