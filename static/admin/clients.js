/** Admin - Clients: the client record shown on Information. Each change saves on change. */

import { adminApi } from "../api.js";
import { card, esc, rerender, tryInline } from "../ui.js";

const HINT = "Name, date of birth and sex as shown on each plan's Information page. A client with plans cannot be deleted.";

export async function render(root, options) {
  const clients = await adminApi.get("/clients/");
  root.innerHTML = card("Clients", body(clients, options.canEdit), HINT);
  wire(root, options);
}

function fields(c, off) {
  const input = (field, label, type, max) => `<label class="field"><span>${label}</span>
    <input type="${type}" value="${esc(c[field] ?? "")}" ${max ? `maxlength="${max}"` : `max="${new Date().toISOString().slice(0, 10)}"`}
      data-field="${field}" data-value="${esc(c[field] ?? "")}" ${off}></label>`;
  return input("first_name", "First name", "text", 100) + input("last_name", "Last name", "text", 100)
    + input("date_of_birth", "Date of birth", "date") + input("sex", "Sex", "text", 50);
}

function body(clients, canEdit) {
  const off = canEdit ? "" : "disabled";
  const rows = clients.map((c) => {
    const plans = c.plan_count ? `${c.plan_count} ${c.plan_count === 1 ? "plan" : "plans"}` : "No plans";
    const remove = canEdit
      ? `<button type="button" class="link danger" data-delete="${c.id}" ${c.plan_count ? `disabled title="Has treatment plans"` : ""}>Delete</button>`
      : "";
    return `<li class="client-row" data-client="${c.id}">${fields(c, off)}
      <span class="client-plans">${plans}</span>${remove}
      <p class="err" data-client-err="${c.id}"></p></li>`;
  }).join("");
  const add = canEdit
    ? `<div class="client-add">
        <label class="field"><span>First name</span><input type="text" id="new-first" maxlength="100"></label>
        <label class="field"><span>Last name</span><input type="text" id="new-last" maxlength="100"></label>
        <label class="field"><span>Date of birth</span><input type="date" id="new-dob" max="${new Date().toISOString().slice(0, 10)}"></label>
        <label class="field"><span>Sex</span><input type="text" id="new-sex" maxlength="50"></label>
        <button type="button" data-add-client>Add client</button>
      </div><p class="err" id="new-client-err"></p>`
    : "";
  return `<ul class="client-list">${rows}</ul>${add}`;
}

function wire(root, options) {
  const redraw = () => rerender(root, render, options);

  root.addEventListener("change", async (event) => {
    const el = event.target.closest("[data-field]");
    if (!el) return;
    const id = el.closest("[data-client]").dataset.client;
    dispatchEvent(new Event("tp:saving"));
    const saved = await tryInline(root.querySelector(`[data-client-err="${id}"]`),
      () => adminApi.patch(`/clients/${id}/`, { [el.dataset.field]: el.value }));
    if (!saved) {
      el.value = el.dataset.value;
      return;
    }
    el.dataset.value = el.value;
    dispatchEvent(new Event("tp:saved"));
  });

  root.addEventListener("click", async (event) => {
    if (event.target.closest("[data-add-client]")) await addClient(root, redraw);
    const del = event.target.closest("[data-delete]");
    if (del && confirm("Delete this client? Their guardians and insurance are deleted too.")) {
      dispatchEvent(new Event("tp:saving"));
      const done = await tryInline(root.querySelector(`[data-client-err="${del.dataset.delete}"]`),
        () => adminApi.del(`/clients/${del.dataset.delete}/`).then(() => true));
      if (done) await redraw();
    }
  });
}

async function addClient(root, redraw) {
  dispatchEvent(new Event("tp:saving"));
  const body = {
    first_name: root.querySelector("#new-first").value,
    last_name: root.querySelector("#new-last").value,
    date_of_birth: root.querySelector("#new-dob").value,
    sex: root.querySelector("#new-sex").value,
  };
  if (await tryInline(root.querySelector("#new-client-err"), () => adminApi.post("/clients/", body), "Enter a first and last name.")) await redraw();
}
