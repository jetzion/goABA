/** Medication page: no-medication checkbox, medication rows, and a draft form for new rows. */

import { api } from "../api.js";
import { bindAutosave, bindDraft, bindRowActions, draftHtml, rowListHtml } from "../form.js";
import { card, rerender } from "../ui.js";

const DEFS = [
  { name: "medication_name", label: "Medication" },
  { name: "dosage", label: "Dosage" },
  { name: "start_date", label: "Start month", type: "month" },
  { name: "physician_name", label: "Prescribing physician" },
  { name: "reason", label: "Reason for taking" },
];

export async function render(container, planId) {
  const base = `/${planId}/pages/medications/`;
  const data = await api.get(base);
  const rows = data.medications;

  container.innerHTML = `
    <ul class="page-errors" hidden></ul>
    <div class="field" data-wrap="no_medication">
      <label class="flag"><input type="checkbox" data-flag ${data.no_medication ? "checked" : ""}>
        No medication taken by the client</label>
      <small class="err"></small>
    </div>
    ${data.no_medication ? "" : card("Medications", rowListHtml(rows, DEFS, "medication") + draftHtml(DEFS, "medication"), "Each medication needs all five fields.")}`;

  const refresh = () => rerender(container, render, planId);

  container.querySelector("[data-flag]").addEventListener("change", async (event) => {
    if (event.target.checked && rows.length) {
      if (!confirm("Checking this deletes every medication on this page. Continue?")) {
        event.target.checked = false;
        return;
      }
      await api.del(`${base}all/`);
    }
    await api.patch(base, { no_medication: event.target.checked });
    await refresh();
  });

  if (data.no_medication) return;

  bindAutosave(container, ({ name, value, rowId }) => api.patch(`${base}${rowId}/`, { [name]: value }));
  bindRowActions(container, { noun: "medication", remove: (id) => api.del(`${base}${id}/`), refresh });
  bindDraft(container, {
    beforeOpen: () => data.no_medication === null && api.patch(base, { no_medication: false }),
    post: (values) => api.post(base, values),
    refresh,
  });
}
