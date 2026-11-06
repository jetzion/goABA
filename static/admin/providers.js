/** Admin - Providers: clinicians who own plans and are assigned to clients. Each change saves on change. */

import { adminApi } from "../api.js";
import { card, esc, rerender, tryInline } from "../ui.js";

const HINT = "Turning a provider off keeps their plans, assignments and user link, but they can no longer be newly assigned or linked.";

export async function render(root, options) {
  const providers = await adminApi.get("/providers/");
  root.innerHTML = card("Providers", body(providers, options.canEdit), HINT);
  wire(root, options);
}

function usage(p) {
  const parts = [
    p.user ? `Signs in as ${esc(p.user)}` : "No user",
    `${p.assignments} ${p.assignments === 1 ? "client" : "clients"}`,
    `${p.plans} ${p.plans === 1 ? "plan" : "plans"}`,
  ];
  return parts.join(" · ");
}

function body(providers, canEdit) {
  const off = canEdit ? "" : "disabled";
  const rows = providers.map((p) => {
    const used = p.user || p.assignments || p.plans;
    const remove = canEdit
      ? `<button type="button" class="link danger" data-delete="${p.id}" ${used ? `disabled title="In use. Turn it off instead."` : ""}>Delete</button>`
      : "";
    return `<li class="provider-row${p.active ? "" : " is-off"}" data-provider="${p.id}">
      <label class="field"><span>Name</span><input type="text" value="${esc(p.display_name)}" maxlength="255" data-field="display_name" data-value="${esc(p.display_name)}" ${off}></label>
      <label class="name-active"><input type="checkbox" data-field="active" ${p.active ? "checked" : ""} ${off}><span>Active</span></label>
      <span class="provider-usage">${usage(p)}</span>${remove}
      <p class="err" data-provider-err="${p.id}"></p>
    </li>`;
  }).join("");
  const add = canEdit
    ? `<div class="add-item provider-add"><label class="field"><span class="sr-only">New provider name</span>
        <input type="text" id="new-provider" maxlength="255" placeholder="New provider name, e.g. Riley Tran, RBT"></label>
        <button type="button" data-add-provider>Add provider</button></div><p class="err" id="new-provider-err"></p>`
    : "";
  return `<ul class="provider-list">${rows}</ul>${add}`;
}

function wire(root, options) {
  const redraw = () => rerender(root, render, options);

  root.addEventListener("change", async (event) => {
    const el = event.target.closest("[data-field]");
    if (!el) return;
    const id = el.closest("[data-provider]").dataset.provider;
    const field = el.dataset.field;
    dispatchEvent(new Event("tp:saving"));
    const saved = await tryInline(root.querySelector(`[data-provider-err="${id}"]`),
      () => adminApi.patch(`/providers/${id}/`, { [field]: field === "active" ? el.checked : el.value }), "Enter a name.");
    if (!saved) {
      if (field === "active") el.checked = !el.checked;
      else el.value = el.dataset.value;
      return;
    }
    if (field === "active") return redraw();
    el.dataset.value = el.value;
    dispatchEvent(new Event("tp:saved"));
  });

  root.addEventListener("click", async (event) => {
    if (event.target.closest("[data-add-provider]")) await addProvider(root, redraw);
    const del = event.target.closest("[data-delete]");
    if (del && confirm("Delete this provider?")) {
      dispatchEvent(new Event("tp:saving"));
      const done = await tryInline(root.querySelector(`[data-provider-err="${del.dataset.delete}"]`),
        () => adminApi.del(`/providers/${del.dataset.delete}/`).then(() => true));
      if (done) await redraw();
    }
  });

  root.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && event.target.id === "new-provider") addProvider(root, redraw);
  });
}

async function addProvider(root, redraw) {
  dispatchEvent(new Event("tp:saving"));
  const body = { display_name: root.querySelector("#new-provider").value };
  if (await tryInline(root.querySelector("#new-provider-err"), () => adminApi.post("/providers/", body), "Enter a name.")) await redraw();
}
