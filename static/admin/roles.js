/** Admin - Roles: the role list (add, rename, delete) and the access matrix. Each cell saves on change. */

import { adminApi } from "../api.js";
import { KEY_LABELS } from "../labels.js";
import { card, esc, rerender, tryInline } from "../ui.js";

const LEVEL_TEXT = { none: "None", view: "View", edit: "Edit" };
const ACTION_TEXT = { none: "Not allowed", edit: "Allowed" };
const NAME_HINT = "Enter 1 to 100 characters.";
const GROUPS = [["page", "Plan pages"], ["action", "Actions"], ["admin", "Admin pages"]];
const LOCK = `<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>`;

let pickedRole = null;

export async function render(root, options) {
  const data = await adminApi.get("/roles/");
  const roles = data.roles;
  if (!roles.some((r) => r.id === pickedRole)) pickedRole = (roles.find((r) => !r.locked) ?? roles[0]).id;
  root.innerHTML = card("Roles", roleList(roles, options.canEdit), "Each user has one role. Admin is locked and always has full access.")
    + card("Access", matrix(data.keys, roles, options.canEdit), "What each role can do on every page. Edit includes View. Changes save right away.");
  showPicked(root);
  wire(root, options);
}

function roleList(roles, canEdit) {
  const rows = roles.map((r) => {
    const editable = canEdit && !r.locked;
    const meta = r.locked ? `${LOCK}Full access, locked` : `${r.user_count} ${r.user_count === 1 ? "user" : "users"}`;
    const remove = editable
      ? `<button type="button" class="link danger" data-delete="${r.id}" ${r.user_count ? `disabled title="Give its users another role first"` : ""}>Delete</button>`
      : "";
    return `<li class="role-row">
      <label class="field"><span class="sr-only">Role name</span>
        <input type="text" value="${esc(r.name)}" maxlength="100" data-rename="${r.id}" ${editable ? "" : "disabled"}></label>
      <span class="role-meta">${meta}</span>${remove}
      <p class="err" data-role-err="${r.id}"></p>
    </li>`;
  }).join("");
  const add = canEdit
    ? `<div class="add-item"><label class="field"><span class="sr-only">New role name</span>
        <input type="text" id="new-role" maxlength="100" placeholder="New role name"></label>
        <button type="button" data-add-role>Add role</button></div><p class="err" id="new-role-err"></p>`
    : "";
  return `<ul class="role-list">${rows}</ul>${add}`;
}

function matrix(keys, roles, canEdit) {
  const head = roles.map((r) => `<th scope="col" data-col="${r.id}">${r.locked ? LOCK : ""}${esc(r.name)}</th>`).join("");
  const body = GROUPS.map(([group, title]) => {
    const rows = keys.filter((k) => k.group === group).map((k) => `<tr><th scope="row">${esc(KEY_LABELS[k.key] ?? k.key)}</th>${roles.map((r) => cell(k, r, canEdit)).join("")}</tr>`);
    return `<tr class="matrix-group"><th scope="colgroup" colspan="${roles.length + 1}">${title}</th></tr>${rows.join("")}`;
  }).join("");
  const pick = `<label class="field matrix-pick"><span>Show role</span><select data-pick>${roles.map((r) => `<option value="${r.id}">${esc(r.name)}</option>`).join("")}</select></label>`;
  return `${pick}<div class="matrix-wrap"><table class="matrix"><thead><tr><th scope="col">Access</th>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}

function cell(key, role, canEdit) {
  const level = role.permissions[key.key];
  const text = key.group === "action" ? ACTION_TEXT : LEVEL_TEXT;
  const label = `${role.name}: ${KEY_LABELS[key.key] ?? key.key}`;
  const opts = key.allowed.map((l) => `<option value="${l}" ${l === level ? "selected" : ""}>${text[l]}</option>`).join("");
  return `<td data-col="${role.id}"><select data-cell data-role="${role.id}" data-key="${key.key}" data-level="${level}" aria-label="${esc(label)}" ${canEdit && !role.locked ? "" : "disabled"}>${opts}</select></td>`;
}

/** Phones show one role column at a time. */
function showPicked(root) {
  root.querySelector("[data-pick]").value = String(pickedRole);
  root.querySelectorAll(".matrix [data-col]").forEach((el) => el.classList.toggle("col-off", el.dataset.col !== String(pickedRole)));
}

function wire(root, options) {
  const redraw = () => rerender(root, render, options);

  root.addEventListener("change", async (event) => {
    const el = event.target;
    if (el.matches("[data-pick]")) {
      pickedRole = Number(el.value);
      showPicked(root);
    } else if (el.matches("[data-cell]")) {
      dispatchEvent(new Event("tp:saving"));
      await adminApi.put(`/roles/${el.dataset.role}/permissions/${el.dataset.key}/`, { level: el.value });
      el.dataset.level = el.value;
      dispatchEvent(new Event("tp:saved"));
    } else if (el.matches("[data-rename]")) {
      dispatchEvent(new Event("tp:saving"));
      const errEl = root.querySelector(`[data-role-err="${el.dataset.rename}"]`);
      if (await tryInline(errEl, () => adminApi.patch(`/roles/${el.dataset.rename}/`, { name: el.value }), NAME_HINT)) await redraw();
    }
  });

  root.addEventListener("click", async (event) => {
    if (event.target.closest("[data-add-role]")) await addRole(root, redraw);
    const del = event.target.closest("[data-delete]");
    if (del && confirm("Delete this role?")) {
      dispatchEvent(new Event("tp:saving"));
      await adminApi.del(`/roles/${del.dataset.delete}/`);
      await redraw();
    }
  });

  root.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && event.target.id === "new-role") addRole(root, redraw);
  });
}

async function addRole(root, redraw) {
  const input = root.querySelector("#new-role");
  dispatchEvent(new Event("tp:saving"));
  const role = await tryInline(root.querySelector("#new-role-err"), () => adminApi.post("/roles/", { name: input.value }), NAME_HINT);
  if (!role) return;
  pickedRole = role.id;
  await redraw();
}
