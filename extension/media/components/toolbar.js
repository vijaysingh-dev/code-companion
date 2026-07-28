// Composer pickers row: Model / Effort / Mode as custom dropdowns, plus the
// backend health dot. Effort is disabled when the chosen model can't reason.

import { createDropdown } from "./dropdown.js";

const HEALTH = {
  unknown: ["cc-unknown", "Checking backend…"],
  healthy: ["cc-healthy", "Backend healthy"],
  unreachable: ["cc-unreachable", "Backend unreachable"],
};

const EFFORT_OPTIONS = [
  { value: "low", name: "Low" },
  { value: "medium", name: "Medium" },
  { value: "high", name: "High" },
  { value: "max", name: "Max" },
];

const MODE_OPTIONS = [
  { value: "ask", name: "Ask", desc: "Answers only — no context", icon: "?" },
  { value: "plan", name: "Plan", desc: "Reads & plans — no edits", icon: "◇" },
  { value: "agent", name: "Agent", desc: "Edits files; asks before risky commands", icon: "◆" },
];

export function createToolbar({ modelEl, effortEl, modeEl, status }) {
  let models = [];

  const model = createDropdown({ container: modelEl, label: "", onChange: syncEffort });
  const effort = createDropdown({ container: effortEl, label: "Effort" });
  const mode = createDropdown({ container: modeEl, label: "Mode", align: "right" });

  effort.setOptions(EFFORT_OPTIONS);
  effort.setValue("medium");
  mode.setOptions(MODE_OPTIONS);
  mode.setValue("agent");

  function setModels(next) {
    models = next;
    model.setOptions(models.map((m, i) => ({ value: String(i), name: `${m.provider_name} ${m.model}` })));
    syncEffort();
  }

  function syncEffort() {
    const chosen = models[Number(model.getValue())];
    effort.setDisabled(!chosen || !chosen.supports_effort);
  }

  // Reflect an opened session's provider/model in the picker (no-op if not listed).
  function select(providerId, modelId) {
    const index = models.findIndex((m) => m.provider === providerId && m.model === modelId);
    if (index >= 0) {
      model.setValue(String(index));
      syncEffort();
    }
  }

  function getSelection() {
    const chosen = models[Number(model.getValue())];
    return {
      mode: mode.getValue(),
      provider: chosen ? chosen.provider : "",
      model: chosen ? chosen.model : "",
      effort: effort.getValue(),
    };
  }

  function setHealth(state) {
    const [cls, title] = HEALTH[state] ?? HEALTH.unknown;
    status.className = `cc-dot ${cls}`;
    status.title = title;
  }

  return { setModels, getSelection, setHealth, select };
}
