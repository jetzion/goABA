/** Education page: not-attending checkbox, otherwise the school detail fields. */

import { api } from "../api.js";
import { bindAutosave, fieldsHtml, options } from "../form.js";
import { card, rerender } from "../ui.js";

function defs(o) {
  return [
    { name: "education_setting", label: "Education setting", type: "select", options: o.EDUCATION_SETTINGS },
    { name: "number_of_hours_per_week", label: "Number of hours per week", type: "number", step: "0.1" },
    { name: "school_name", label: "School name" },
    { name: "school_phone_number", label: "School phone number", type: "tel" },
    { name: "evaluation_status", label: "Client's education evaluation status", type: "select", options: o.EVALUATION_STATUSES },
    { name: "evaluation_date", label: "Evaluation date", type: "date" },
    { name: "iep_or_504_in_place", label: "IEP or 504 in place", type: "select", options: o.IEP_OR_504 },
    { name: "education_support", label: "Educational support" },
    { name: "classroom_setting", label: "Child's current classroom setting", type: "select", options: o.CLASSROOM_SETTINGS },
    { name: "attitude_towards_school", label: "Child's attitude towards school", type: "select", options: o.SCHOOL_ATTITUDES },
    { name: "education_description", label: "Education description", type: "rich" },
    { name: "focus_area_description", label: "Focus area description", type: "rich" },
  ];
}

export async function render(container, planId) {
  const fields = defs(await options());
  const url = `/${planId}/pages/education/`;
  const data = await api.get(url);

  container.innerHTML = `
    <ul class="page-errors" hidden></ul>
    <div class="field" data-wrap="not_attending_school">
      <label class="flag"><input type="checkbox" data-flag ${data.not_attending_school ? "checked" : ""}> Child is not attending school</label>
      <small class="err"></small>
    </div>
    ${data.not_attending_school ? "" : card("School", fieldsHtml(fields, data), "Evaluation status and date are optional. Homeschool needs no school name or phone.")}`;

  container.querySelector("[data-flag]").addEventListener("change", async (event) => {
    const checked = event.target.checked;
    const hasData = fields.some((f) => data[f.name] !== null);
    if (checked && hasData && !confirm("Checking this clears every education field. Continue?")) {
      event.target.checked = false;
      return;
    }
    const cleared = checked ? Object.fromEntries(fields.map((f) => [f.name, null])) : {};
    await api.patch(url, { not_attending_school: checked, ...cleared });
    await rerender(container, render, planId);
  });

  bindAutosave(container, ({ name, value }) => api.patch(url, { [name]: value }));
}
