// Context pills row. Markup (the two add buttons) lives in index.html; this
// only wires the buttons and clones #tpl-pill for each attached file.

export function createContextBar({ root, pills, onAddActive, onPick, onRemove }) {
  root.querySelector('[data-action="add-active"]').addEventListener("click", onAddActive);
  root.querySelector('[data-action="pick"]').addEventListener("click", onPick);

  const template = document.getElementById("tpl-pill");

  function render(files) {
    pills.replaceChildren();
    for (const file of files) {
      const pill = template.content.firstElementChild.cloneNode(true);
      pill.title = file.path;
      pill.querySelector(".cc-pill-name").textContent = file.path;
      pill.querySelector(".cc-pill-x").addEventListener("click", () => onRemove(file.fsPath));
      pills.appendChild(pill);
    }
  }

  return { render };
}
