// A custom picker: a compact "Label · Value" button that opens a menu of rows,
// each an icon + name + description (Continue-style). Replaces native <select>
// so we can show per-option descriptions/icons. CSP-safe — no external assets.
//
// Options are { value, name, desc?, icon? }. One menu is open at a time.

export function createDropdown({ container, label, onChange, align }) {
  const shell = document.getElementById("tpl-dd").content.firstElementChild.cloneNode(true);
  const itemTemplate = document.getElementById("tpl-dd-item");
  container.appendChild(shell);

  const btn = shell.querySelector(".cc-dd-btn");
  const valueEl = shell.querySelector(".cc-dd-value");
  const labelEl = shell.querySelector(".cc-dd-label");
  if (label) {
    labelEl.textContent = label;
  } else {
    labelEl.remove();
  }

  const menu = shell.querySelector(".cc-dd-menu");
  if (align === "right") {
    menu.classList.add("align-right"); // open leftward so a right-edge picker isn't clipped
  }
  let options = [];
  let value = null;
  let disabled = false;

  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    menu.hidden ? open() : close();
  });

  function open() {
    if (disabled) {
      return;
    }
    closeAllMenus();
    menu.hidden = false;
    document.addEventListener("click", onOutside, true);
  }

  function close() {
    menu.hidden = true;
    document.removeEventListener("click", onOutside, true);
  }

  function onOutside(e) {
    if (!container.contains(e.target)) {
      close();
    }
  }

  function setOptions(next) {
    options = next;
    menu.replaceChildren();
    for (const opt of options) {
      const item = itemTemplate.content.firstElementChild.cloneNode(true);
      item.dataset.value = opt.value;
      item.querySelector(".cc-dd-icon").textContent = opt.icon ?? "";
      item.querySelector(".cc-dd-name").textContent = opt.name;
      const desc = item.querySelector(".cc-dd-desc");
      if (opt.desc) {
        desc.textContent = opt.desc;
      } else {
        desc.remove();
      }
      item.addEventListener("click", (e) => {
        e.stopPropagation();
        setValue(opt.value);
        close();
        onChange?.(opt.value);
      });
      menu.appendChild(item);
    }
    setValue(options.some((o) => o.value === value) ? value : (options[0]?.value ?? null));
  }

  function setValue(next) {
    value = next;
    const chosen = options.find((o) => o.value === value);
    valueEl.textContent = chosen ? chosen.name : "";
    for (const item of menu.children) {
      item.setAttribute("aria-checked", String(item.dataset.value === value));
    }
  }

  function setDisabled(next) {
    disabled = next;
    shell.classList.toggle("disabled", next);
    if (next) {
      close();
    }
  }

  return { setOptions, setValue, getValue: () => value, setDisabled };
}

function closeAllMenus() {
  for (const menu of document.querySelectorAll(".cc-dd-menu:not([hidden])")) {
    menu.hidden = true;
  }
}
