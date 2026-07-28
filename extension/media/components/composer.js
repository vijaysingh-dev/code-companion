// Input behavior. The textarea + button markup lives in index.html; this wires
// auto-grow, Enter-to-send (Shift+Enter = newline), and the Send/Stop toggle.

export function createComposer({ input, button, onSend, onStop }) {
  let streaming = false;

  input.addEventListener("input", autoGrow);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  });
  button.addEventListener("click", () => (streaming ? onStop() : submit()));

  function submit() {
    const text = input.value.trim();
    if (!text) {
      return;
    }
    onSend(text);
    input.value = "";
    autoGrow();
  }

  function autoGrow() {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 180)}px`;
  }

  function setStreaming(next) {
    streaming = next;
    button.title = next ? "Stop" : "Send";
    button.classList.toggle("stop", next); // CSS swaps the arrow/stop SVGs
  }

  function focus() {
    input.focus();
  }

  return { setStreaming, focus };
}
