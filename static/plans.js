/** Plans: every plan grouped by client, and the New plan form. */

import { api } from "./api.js";
import { card, esc, tryInline } from "./ui.js";

const DATE = new Intl.DateTimeFormat(undefined, { year: "numeric", month: "short", day: "numeric" });

export async function render(root, { canCreate, isProvider }) {
  const data = await api.get("/");
  const canCopy = canCreate && isProvider;
  root.innerHTML = (canCreate ? card("New plan", newPlan(data, isProvider), "Pick the client and the plan's bay.") : "")
    + card("Plans", planList(data.plans, canCopy), canCopy ? "Newest first, grouped by client. Start the next plan from an existing one to copy every page." : "Newest first, grouped by client.");
  root.querySelector("[data-create-plan]")?.addEventListener("click", () => create(root));
  root.addEventListener("click", (event) => {
    const button = event.target.closest("[data-clone]");
    if (button) cloneFrom(button);
  });
}

/** Copy every page of a plan into a new draft for the same client, then open it. */
async function cloneFrom(button) {
  if (!confirm(`Start a new draft plan for ${button.dataset.client}, copying every page of Plan ${button.dataset.clone}?`)) return;
  button.disabled = true;
  const plan = await api.post(`/${button.dataset.clone}/clone/`);
  location.hash = `#/plan/${plan.id}`;
}

function newPlan({ clients, bays }, isProvider) {
  if (!isProvider) {
    return `<p class="muted">Your user is not linked to a provider, so you cannot own a plan. An admin can link one on Admin - Users.</p>`;
  }
  if (!clients.length) {
    return `<p class="muted">You are not assigned to any client yet. An admin can assign you on Admin - Client assignment.</p>`;
  }
  return `<div class="plan-new">
      <label class="field"><span>Client</span><select id="new-plan-client"><option value=""></option>
        ${clients.map((c) => `<option value="${c.id}">${esc(c.name)}</option>`).join("")}</select></label>
      <label class="field"><span>Bay</span><select id="new-plan-bay"><option value=""></option>
        ${bays.map((b) => `<option value="${esc(b)}">Bay ${esc(b)}</option>`).join("")}</select></label>
      <button type="button" data-create-plan>Create plan</button>
    </div><p class="err" id="new-plan-err"></p>`;
}

function planList(plans, canCopy) {
  if (!plans.length) return `<p class="empty-note">No plans yet.</p>`;
  const clients = [...new Map(plans.map((p) => [p.client_id, p.client_name])).entries()];
  return clients.map(([clientId, name]) => `
    <h3 class="plan-client">${esc(name)}</h3>
    <ul class="plan-list">${plans.filter((p) => p.client_id === clientId).map((p) => planRow(p, canCopy)).join("")}</ul>`).join("");
}

function planRow(p, canCopy) {
  const status = p.status === "signed"
    ? `<span class="plan-status is-signed">Signed by ${esc(p.signature)}</span>`
    : `<span class="plan-status">Draft</span>`;
  const copy = canCopy
    ? `<button type="button" class="secondary plan-copy" data-clone="${p.id}" data-client="${esc(p.client_name)}">New plan from this</button>`
    : "";
  return `<li class="plan-item"><a class="plan-row" href="#/plan/${p.id}">
      <strong>Plan ${p.id}</strong><span>Bay ${esc(p.bay ?? "-")}</span>${status}
      <span class="plan-meta">Started ${DATE.format(new Date(p.date_treatment_plan_started))}${p.owner ? ` by ${esc(p.owner)}` : ""}</span>
    </a>${copy}</li>`;
}

async function create(root) {
  const clientId = root.querySelector("#new-plan-client").value;
  const bay = root.querySelector("#new-plan-bay").value;
  const err = root.querySelector("#new-plan-err");
  if (!clientId || !bay) {
    err.textContent = "Pick a client and a bay.";
    return;
  }
  const plan = await tryInline(err, () => api.post("/", { client_id: Number(clientId), bay }));
  if (plan) location.hash = `#/plan/${plan.id}`;
}
