/** Admin - Goal names: the catalog goal pickers offer, grouped by focus area. Each change saves on change. */

import { adminApi } from "../api.js";
import { card, esc, rerender, tryInline } from "../ui.js";

const SECTION_HINT = "Parent training names appear in PCG, Behavior change in BRG, and every other area in SAG. Turning a name off hides it from goal pickers; goals that already use it stay.";

export async function render(root, options) {
  const data = await adminApi.get("/goal_names/");
  root.innerHTML = card("Goal names", body(data, options.canEdit), SECTION_HINT);
  wire(root, options);
}

function body({ goal_names: names, focus_areas: areas }, canEdit) {
  const off = canEdit ? "" : "disabled";
  const groups = [...new Set(names.map((n) => n.focus_area))].map((area) => `
    <h3 class="name-area">${esc(area)}</h3>
    <ul class="name-list">${names.filter((n) => n.focus_area === area).map((n) => row(n, off, canEdit)).join("")}</ul>`).join("");
  const add = canEdit
    ? `<div class="name-add">
        <label class="field"><span>Prefix</span><input type="text" id="new-prefix" maxlength="20"></label>
        <label class="field"><span>Label</span><input type="text" id="new-label" maxlength="255"></label>
        <label class="field"><span>Focus area</span><input type="text" id="new-area" maxlength="100" list="focus-areas"></label>
        <button type="button" data-add-name>Add goal name</button>
      </div><p class="err" id="new-name-err"></p>`
    : "";
  const datalist = `<datalist id="focus-areas">${areas.map((a) => `<option value="${esc(a)}">`).join("")}</datalist>`;
  return `${datalist}${groups}${add}`;
}

function row(n, off, canEdit) {
  const used = n.in_use ? `Used by ${n.in_use} ${n.in_use === 1 ? "goal" : "goals"}` : "Not used";
  const remove = canEdit
    ? `<button type="button" class="link danger" data-delete="${n.id}" ${n.in_use ? `disabled title="Used on plans. Turn it off instead."` : ""}>Delete</button>`
    : "";
  return `<li class="name-row${n.active ? "" : " is-off"}" data-name="${n.id}">
    <label class="field"><span>Prefix</span><input type="text" value="${esc(n.prefix)}" maxlength="20" data-field="prefix" data-value="${esc(n.prefix)}" ${off}></label>
    <label class="field"><span>Label</span><input type="text" value="${esc(n.label)}" maxlength="255" data-field="label" data-value="${esc(n.label)}" ${off}></label>
    <label class="field"><span>Focus area</span><input type="text" value="${esc(n.focus_area)}" maxlength="100" list="focus-areas" data-field="focus_area" data-value="${esc(n.focus_area)}" ${off}></label>
    <label class="name-active"><input type="checkbox" data-field="active" ${n.active ? "checked" : ""} ${off}><span>Active</span></label>
    <span class="name-used">${used}</span>${remove}
    <p class="err" data-name-err="${n.id}"></p>
  </li>`;
}

function wire(root, options) {
  const redraw = () => rerender(root, render, options);

  root.addEventListener("change", async (event) => {
    const el = event.target.closest("[data-field]");
    if (!el) return;
    const id = el.closest("[data-name]").dataset.name;
    const field = el.dataset.field;
    const value = field === "active" ? el.checked : el.value;
    dispatchEvent(new Event("tp:saving"));
    const saved = await tryInline(root.querySelector(`[data-name-err="${id}"]`), () => adminApi.patch(`/goal_names/${id}/`, { [field]: value }));
    if (!saved) {
      if (field === "active") el.checked = !el.checked;
      else el.value = el.dataset.value;
      return;
    }
    if (field === "focus_area" || field === "active") return redraw();
    el.dataset.value = el.value;
    dispatchEvent(new Event("tp:saved"));
  });

  root.addEventListener("click", async (event) => {
    if (event.target.closest("[data-add-name]")) await addName(root, redraw);
    const del = event.target.closest("[data-delete]");
    if (del && confirm("Delete this goal name?")) {
      dispatchEvent(new Event("tp:saving"));
      const done = await tryInline(root.querySelector(`[data-name-err="${del.dataset.delete}"]`),
        () => adminApi.del(`/goal_names/${del.dataset.delete}/`).then(() => true));
      if (done) await redraw();
    }
  });
}

async function addName(root, redraw) {
  dispatchEvent(new Event("tp:saving"));
  const body = {
    prefix: root.querySelector("#new-prefix").value,
    label: root.querySelector("#new-label").value,
    focus_area: root.querySelector("#new-area").value,
  };
  if (await tryInline(root.querySelector("#new-name-err"), () => adminApi.post("/goal_names/", body), "Fill in prefix, label and focus area.")) await redraw();
}
