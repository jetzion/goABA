/** Admin - Users: who can sign in, their email, role, provider link and temporary password. Each change saves on change. */

import { adminApi } from "../api.js";
import { card, esc, rerender, tryInline } from "../ui.js";

const HINT = "Each user signs in with their email. Give a new user a temporary password; they choose their own at first sign-in. A provider can be linked to one user only.";
const TEXT_FIELDS = new Set(["display_name", "email"]);

export async function render(root, options) {
  const data = await adminApi.get("/users/");
  root.innerHTML = card("Users", userList(data, options), HINT);
  wire(root, options);
}

function roleOptions(roles, selected) {
  return roles.map((r) => `<option value="${r.id}" ${r.id === selected ? "selected" : ""}>${esc(r.name)}</option>`).join("");
}

function providerOptions(providers, selected) {
  return `<option value="">Not a provider</option>`
    + providers.map((p) => `<option value="${p.id}" ${p.id === selected ? "selected" : ""}>${esc(p.name)}</option>`).join("");
}

function passwordState(u) {
  if (!u.has_password) return `<span class="user-state is-off">No password</span>`;
  if (u.must_change_password) return `<span class="user-state is-temp">Temporary password</span>`;
  return `<span class="user-state is-on">Can sign in</span>`;
}

function userRow(u, { roles, providers }, { canEdit, me }) {
  const off = canEdit ? "" : "disabled";
  const self = u.id === me;
  const reset = canEdit && !self
    ? `<button type="button" class="link" data-reset="${u.id}">Set temporary password</button>
       <span class="user-reset" data-reset-form="${u.id}" hidden>
         <input type="text" autocomplete="off" spellcheck="false" placeholder="8 or more characters" aria-label="Temporary password for ${esc(u.display_name)}">
         <button type="button" class="secondary" data-reset-save="${u.id}">Set</button></span>`
    : "";
  return `<li class="user-row" data-user="${u.id}">
      <label class="field"><span>Name</span><input type="text" value="${esc(u.display_name)}" maxlength="255" data-field="display_name" data-value="${esc(u.display_name)}" ${off}></label>
      <label class="field"><span>Email</span><input type="email" value="${esc(u.email ?? "")}" maxlength="255" data-field="email" data-value="${esc(u.email ?? "")}" ${off}></label>
      <label class="field"><span>Role</span><select data-field="role_id" data-value="${u.role_id}" ${off}>${roleOptions(roles, u.role_id)}</select></label>
      <label class="field"><span>Provider</span><select data-field="provider_id" data-value="${u.provider_id ?? ""}" ${off}>${providerOptions(providers, u.provider_id)}</select></label>
      ${canEdit ? (self ? `<span class="user-you">You</span>` : `<button type="button" class="link danger" data-delete="${u.id}">Delete</button>`) : ""}
      <div class="user-sign-in">${passwordState(u)}${self ? `<a href="#/password">Change your password</a>` : reset}</div>
      <p class="err" data-user-err="${u.id}"></p>
    </li>`;
}

function userList(data, options) {
  const rows = data.users.map((u) => userRow(u, data, options)).join("");
  const add = options.canEdit
    ? `<div class="user-add">
        <label class="field"><span>New user name</span><input type="text" id="new-user" maxlength="255"></label>
        <label class="field"><span>Email</span><input type="email" id="new-user-email" maxlength="255"></label>
        <label class="field"><span>Role</span><select id="new-user-role"><option value="">Choose a role</option>${roleOptions(data.roles, null)}</select></label>
        <button type="button" data-add-user>Add user</button>
      </div><p class="err" id="new-user-err"></p>`
    : "";
  return `<ul class="user-list">${rows}</ul>${add}`;
}

function fieldValue(el) {
  if (TEXT_FIELDS.has(el.dataset.field)) return el.value;
  return el.value === "" ? null : Number(el.value);
}

function wire(root, options) {
  const redraw = () => rerender(root, render, options);
  const errFor = (id) => root.querySelector(`[data-user-err="${id}"]`);

  root.addEventListener("change", async (event) => {
    const el = event.target.closest("[data-field]");
    if (!el) return;
    const userId = el.closest("[data-user]").dataset.user;
    dispatchEvent(new Event("tp:saving"));
    const saved = await tryInline(errFor(userId), () => adminApi.patch(`/users/${userId}/`, { [el.dataset.field]: fieldValue(el) }));
    if (saved) {
      el.dataset.value = el.value;
      dispatchEvent(new Event("tp:saved"));
    } else {
      el.value = el.dataset.value;
    }
  });

  root.addEventListener("click", async (event) => {
    if (event.target.closest("[data-add-user]")) await addUser(root, redraw);
    const reset = event.target.closest("[data-reset]");
    if (reset) {
      reset.hidden = true;
      const form = root.querySelector(`[data-reset-form="${reset.dataset.reset}"]`);
      form.hidden = false;
      form.querySelector("input").focus();
    }
    const save = event.target.closest("[data-reset-save]");
    if (save) {
      const id = save.dataset.resetSave;
      const password = root.querySelector(`[data-reset-form="${id}"] input`).value;
      dispatchEvent(new Event("tp:saving"));
      const done = await tryInline(errFor(id), () => adminApi.post(`/users/${id}/password/`, { password }).then(() => true), "Use 8 or more characters.");
      if (done) await redraw();
    }
    const del = event.target.closest("[data-delete]");
    if (del && confirm("Delete this user? They will no longer be able to sign in.")) {
      dispatchEvent(new Event("tp:saving"));
      const done = await tryInline(errFor(del.dataset.delete), () => adminApi.del(`/users/${del.dataset.delete}/`).then(() => true));
      if (done) await redraw();
    }
  });

  root.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && ["new-user", "new-user-email"].includes(event.target.id)) addUser(root, redraw);
  });
}

async function addUser(root, redraw) {
  if (!root.querySelector("#new-user-role").value) {
    root.querySelector("#new-user-err").textContent = "Choose a role for the new user.";
    return;
  }
  dispatchEvent(new Event("tp:saving"));
  const body = {
    display_name: root.querySelector("#new-user").value,
    email: root.querySelector("#new-user-email").value,
    role_id: Number(root.querySelector("#new-user-role").value),
  };
  if (await tryInline(root.querySelector("#new-user-err"), () => adminApi.post("/users/", body), "Enter a name and a valid email.")) await redraw();
}
