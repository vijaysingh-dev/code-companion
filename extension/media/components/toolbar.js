// Selectors row. The <select>s and their static options (mode, effort) live in
// index.html; this fills the model list and reads the current choice. Effort is
// disabled when the chosen model can't reason.

const HEALTH = {
  unknown: ["cc-unknown", "Checking backend…"],
  healthy: ["cc-healthy", "Backend healthy"],
  unreachable: ["cc-unreachable", "Backend unreachable"],
};

export function createToolbar({ mode, model, effort, status }) {
  let models = [];

  model.addEventListener("change", syncEffort);

  function setModels(next) {
    models = next;
    model.replaceChildren(...models.map((m, i) => new Option(`${m.provider_name} · ${m.model}`, String(i))));
    syncEffort();
  }

  function syncEffort() {
    const chosen = models[Number(model.value)];
    effort.disabled = !chosen || !chosen.supports_effort;
  }

  function getSelection() {
    const chosen = models[Number(model.value)];
    return {
      mode: mode.value,
      provider: chosen ? chosen.provider : "",
      model: chosen ? chosen.model : "",
      effort: effort.value,
    };
  }

  function setHealth(state) {
    const [cls, title] = HEALTH[state] ?? HEALTH.unknown;
    status.className = `cc-dot ${cls}`;
    status.title = title;
  }

  return { setModels, getSelection, setHealth };
}
