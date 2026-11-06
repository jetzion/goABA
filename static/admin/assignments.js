/** Admin - Client assignment: each client's care team (Home BCBA, Substitute BCBAs, BTs). Changes save right away. */

import { adminApi } from "../api.js";
import { card, esc, rerender, tryInline } from "../ui.js";

const HINT = "Who is clinically assigned to each client. This fills the Information care team and the bay 3 provisioning text. Each client has at most one Home BCBA.";

export async function render(root, options) {
  const data = await adminApi.get("/assignments/");
  root.innerHTML = card("Client assignment", body(data, options.canEdit), HINT);
  wire(root, options);
}

function roleOptions(roles, selected) {
  return roles.map((r) => `<option value="${r.value}" ${r.value === selected ? "selected" : ""}>${esc(r.label)}</option>`).join("");
}

function body({ clients, providers, roles }, canEdit) {
  if (!clients.length) return `<p class="empty-note">No clients yet. Add one on Admin - Clients.</p>`;
  return clients.map((c) => {
    const taken = new Set(c.assignments.map((a) => a.provider_id));
    const free = providers.filter((p) => !taken.has(p.id));
    const rows = c.assignments.map((a) => `<li class="assign-row" data-assignment="${a.id}">
        <span class="assign-name">${esc(a.provider)}${a.provider_active ? "" : ' <span class="muted">(turned off)</span>'}</span>
        <label class="field"><span class="sr-only">Role for ${esc(a.provider)}</span>
          <select data-role data-value="${a.role}" ${canEdit ? "" : "disabled"}>${roleOptions(roles, a.role)}</select></label>
        ${canEdit ? `<button type="button" class="link danger" data-remove="${a.id}">Remove</button>` : ""}
      </li>`).join("");
    const add = canEdit && free.length
      ? `<div class="assign-add">
          <label class="field"><span class="sr-only">Provider to assign to ${esc(c.name)}</span><select data-new-provider>
            <option value="">Assign a provider</option>${free.map((p) => `<option value="${p.id}">${esc(p.name)}</option>`).join("")}</select></label>
          <label class="field"><span class="sr-only">Role</span><select data-new-role>${roleOptions(roles, "bt")}</select></label>
          <button type="button" class="secondary" data-add>Assign</button>
        </div>`
      : "";
    return `<section class="assign-client" data-client="${c.id}">
      <h3 class="plan-client">${esc(c.name)}</h3>
      ${rows ? `<ul class="assign-list">${rows}</ul>` : `<p class="muted assign-empty">No one assigned yet.</p>`}
      ${add}<p class="err" data-client-err="${c.id}"></p>
    </section>`;
  }).join("");
}

function wire(root, options) {
  const redraw = () => rerender(root, render, options);
  const errFor = (el) => root.querySelector(`[data-client-err="${el.closest("[data-client]").dataset.client}"]`);

  root.addEventListener("change", async (event) => {
    const el = event.target.closest("[data-role]");
    if (!el) return;
    dispatchEvent(new Event("tp:saving"));
    const id = el.closest("[data-assignment]").dataset.assignment;
    const saved = await tryInline(errFor(el), () => adminApi.patch(`/assignments/${id}/`, { role: el.value }));
    if (!saved) {
      el.value = el.dataset.value;
      return;
    }
    await redraw();
  });

  root.addEventListener("click", async (event) => {
    const add = event.target.closest("[data-add]");
    if (add) {
      const section = add.closest("[data-client]");
      const providerId = section.querySelector("[data-new-provider]").value;
      if (!providerId) {
        errFor(add).textContent = "Pick a provider to assign.";
        return;
      }
      dispatchEvent(new Event("tp:saving"));
      const body = { client_id: Number(section.dataset.client), provider_id: Number(providerId), role: section.querySelector("[data-new-role]").value };
      if (await tryInline(errFor(add), () => adminApi.post("/assignments/", body))) await redraw();
    }
    const remove = event.target.closest("[data-remove]");
    if (remove && confirm("Remove this provider from the client?")) {
      dispatchEvent(new Event("tp:saving"));
      await adminApi.del(`/assignments/${remove.dataset.remove}/`);
      await redraw();
    }
  });
}
