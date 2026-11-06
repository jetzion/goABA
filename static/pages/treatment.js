/** Treatment page: recommendations, start and duration, service hours, and the provisioning statement. */

import { api } from "../api.js";
import { bindAutosave, fieldsHtml, options } from "../form.js";
import { card, esc } from "../ui.js";

const HEADER = [
  { name: "proposed_start_date", label: "Proposed start date", type: "date" },
  { name: "duration_in_months", label: "Duration (months)", type: "number" },
  { name: "recommendations_explanation", label: "Recommendations explanation", type: "rich" },
];

function servicesTable(services, labels, perOptions) {
  const rows = Object.entries(labels).map(([prefix, label]) => {
    const s = services[prefix] ?? { hours: null, units: null, per: null };
    const max = prefix.startsWith("assessment_") ? 8 : 99;
    return `<tr>
      <th scope="row">${esc(label)}</th>
      <td><label class="field" data-wrap="${prefix}_hours"><span class="sr-only">Hours</span>
        <input type="number" min="0" max="${max}" step="1" data-field="${prefix}_hours" value="${s.hours ?? ""}"><small class="err"></small></label></td>
      <td class="units" data-units="${prefix}">${s.units ?? "-"}</td>
      <td><label class="field" data-wrap="${prefix}_per"><span class="sr-only">Per</span>
        <select data-field="${prefix}_per"><option value=""></option>${perOptions.map((o) => `<option ${o === s.per ? "selected" : ""}>${esc(o)}</option>`).join("")}</select>
        <small class="err"></small></label></td>
    </tr>`;
  }).join("");
  return `<div class="field" data-wrap="services"><small class="err"></small></div>
    <div class="table-wrap"><table class="services">
      <thead><tr><th scope="col">Service</th><th scope="col">Hours</th><th scope="col">Units</th><th scope="col">Per</th></tr></thead>
      <tbody>${rows}</tbody></table></div>`;
}

export async function render(container, planId) {
  const o = await options();
  const url = `/${planId}/pages/treatment/`;
  const data = await api.get(url);

  container.innerHTML = `
    <ul class="page-errors" hidden></ul>
    ${card("Recommendation", fieldsHtml(HEADER, data), "When treatment starts, for how long, and why.")}
    ${card("Services", servicesTable(data.services, o.SERVICES, o.SERVICE_PER),
      "Units are hours times 4. 97151 and 97152 together cannot exceed 8 hours. Choose how often for any service with hours.")}
    ${card("Therapy provisioning", data.therapy_provisioning_description
      ? `<p class="statement">${esc(data.therapy_provisioning_description)}</p>`
      : '<p class="muted">No provisioning statement for this plan. Bay 3 plans show one once a behavior technician is assigned.</p>',
      "Set by the plan bay. Not editable.")}`;

  bindAutosave(container, ({ name, value }) => api.patch(url, { [name]: value }));
  container.addEventListener("input", (event) => {
    const prefix = event.target.dataset.field?.replace(/_hours$/, "");
    const cell = prefix && container.querySelector(`[data-units="${prefix}"]`);
    if (cell) cell.textContent = event.target.value === "" ? "-" : Number(event.target.value) * 4;
  });
}
