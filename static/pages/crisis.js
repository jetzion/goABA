/** Crisis page: not-needed checkbox and one crisis plan per maladaptive behavior. */

import { api } from "../api.js";
import { bindAutosave, bindDraft, bindRowActions, draftHtml, options, rowListHtml } from "../form.js";
import { card, esc, rerender } from "../ui.js";

const TEXT_FIELDS = [
  ["operational_definition", "Operational definition"],
  ["antecedent_interventions", "Antecedent interventions/modifications"],
  ["precursors_action_steps", "Precursors with action steps to prevent behavior"],
  ["escalation_intervention_plan", "Behavior intervention plan when escalation occurs"],
  ["follow_up_steps", "Follow-up steps"],
  ["consequence_strategies", "Consequence strategies for behavior prior to escalation"],
];

function planDefs(o, behaviors) {
  return [
    { name: "assessment_behavior_id", label: "Related behavior", type: "select", integer: true, options: behaviors.map((b) => [b.id, b.label]) },
    { name: "crisis_creation_date", label: "Crisis creation date", type: "month" },
    { name: "functional_behavior", label: "Functional behavior", type: "multi", options: o.FUNCTIONAL_BEHAVIORS },
    ...TEXT_FIELDS.map(([name, label]) => ({ name, label, type: "rich" })),
  ];
}

export async function render(container, planId) {
  const o = await options();
  const base = `/${planId}/pages/crisis/`;
  const data = await api.get(base);
  const behaviors = data.available_behaviors;
  const used = new Set(data.plans.map((p) => p.assessment_behavior_id));
  const free = behaviors.filter((b) => !used.has(b.id));
  const defs = planDefs(o, behaviors);

  const plansBody = !behaviors.length
    ? `<p class="muted">Crisis plans are written for maladaptive behaviors. <a href="#/plan/${planId}/assessment">Add behaviors on the Assessment page</a> first.</p>`
    : `${rowListHtml(data.plans, defs, "crisis plan", '<button type="button" class="link" data-fill-template>Fill empty fields with starter text</button>')}
       ${free.length ? draftHtml([{ name: "assessment_behavior_id", label: "Related behavior", type: "select", integer: true, options: free.map((b) => [b.id, b.label]) }], "crisis plan") : '<p class="muted">Every behavior has a crisis plan.</p>'}`;

  container.innerHTML = `
    <ul class="page-errors" hidden></ul>
    <div class="field" data-wrap="no_crisis_plan_needed">
      <label class="flag"><input type="checkbox" data-flag ${data.no_crisis_plan_needed ? "checked" : ""}> Crisis plan for this client not needed</label>
      <small class="err"></small>
    </div>
    ${data.no_crisis_plan_needed ? "" : card("Crisis plans", plansBody, "One plan per maladaptive behavior. Each narrative needs at least 60 characters.")}`;

  const refresh = () => rerender(container, render, planId);

  container.querySelector("[data-flag]").addEventListener("change", async (event) => {
    if (event.target.checked && data.plans.length) {
      if (!confirm("Checking this deletes every crisis plan on this page. Continue?")) {
        event.target.checked = false;
        return;
      }
      for (const p of data.plans) await api.del(`${base}${p.id}/`);
    }
    await api.patch(base, { no_crisis_plan_needed: event.target.checked });
    await refresh();
  });

  if (data.no_crisis_plan_needed || !behaviors.length) return;

  bindAutosave(container, ({ name, value, rowId }) => api.patch(`${base}${rowId}/`, { [name]: value }));
  bindRowActions(container, { noun: "crisis plan", remove: (id) => api.del(`${base}${id}/`), refresh });
  bindDraft(container, { post: (values) => api.post(base, values), refresh });

  container.addEventListener("click", async (event) => {
    if (!event.target.matches("[data-fill-template]")) return;
    const row = event.target.closest("[data-row-id]");
    const plan = data.plans.find((p) => p.id === Number(row.dataset.rowId));
    const templates = await api.get(`${base}templates/`);
    const empty = Object.fromEntries(TEXT_FIELDS.filter(([name]) => !plan[name]).map(([name]) => [name, templates[name]]));
    if (!Object.keys(empty).length) return;
    await api.patch(`${base}${plan.id}/`, empty);
    await refresh();
  });
}
