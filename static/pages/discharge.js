/** Discharge page: four narratives and the reasons to decrease hours or discharge. */

import { api } from "../api.js";
import { bindAutosave, bindChips, chipGroupHtml, fieldsHtml, options } from "../form.js";
import { card, esc, rerender } from "../ui.js";

const OTHER = "Other";
const DEFS = [
  { name: "mastery_of_program_goals", label: "Client's and family's ability to master the program", type: "rich" },
  { name: "titration_plan", label: "Titration plan", type: "rich" },
  { name: "readiness_to_step_down", label: "Client's readiness to step down", type: "rich" },
  { name: "care_coordination", label: "Care coordination", type: "rich" },
];

export async function render(container, planId) {
  const o = await options();
  const base = `/${planId}/pages/discharge/`;
  const data = await api.get(base);
  const other = data.reasons.find((r) => r.reason === OTHER);

  container.innerHTML = `
    <ul class="page-errors" hidden></ul>
    ${card("Discharge planning", fieldsHtml(DEFS, data), "Each narrative needs at least 60 characters.")}
    ${card("Reasons", `
      ${chipGroupHtml("reasons", "Reasons to decrease hours or discharge may include", o.DISCHARGE_REASONS,
        data.reasons.map((r) => ({ id: r.id, value: r.reason })))}
      <label class="field explain-other"><span>Explain other</span>
        <input type="text" maxlength="255" value="${esc(other?.explanation)}" data-explain-other
          placeholder="Needed when Other is selected"></label>`,
      "Pick at least one.")}`;

  const explanation = () => container.querySelector("[data-explain-other]").value.trim() || null;

  bindAutosave(container, ({ name, value }) => api.patch(base, { [name]: value }));
  bindChips(container, {
    add: (_type, reason) => api.post(`${base}reasons/`, reason === OTHER ? { reason, explanation: explanation() } : { reason }),
    remove: (_type, id) => api.del(`${base}reasons/${id}/`),
  });

  container.querySelector("[data-explain-other]").addEventListener("change", async () => {
    const box = container.querySelector(`[data-group="reasons"][data-value="${OTHER}"]`);
    if (!box.checked) return;
    await api.del(`${base}reasons/${box.dataset.id}/`);
    try {
      await api.post(`${base}reasons/`, { reason: OTHER, explanation: explanation() });
    } finally {
      await rerender(container, render, planId);
    }
  });
}
