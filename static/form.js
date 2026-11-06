/**
 * Form engine shared by page modules.
 *
 * A field definition is { name, label, type, options?, step?, wrap? } where type is
 * text | email | tel | number | date | month | goalmonth | time | select | yesno | multi | rich | textarea | checkbox.
 * wrap overrides the name used to match errors to the field; wide: true spans the full row.
 * Select options are strings or [value, label] pairs; integer: true sends the value as a number.
 * Inputs carry data-field; inputs inside a row carry the row id via data-row-id on an ancestor.
 */

import { esc } from "./ui.js";

let optionsCache;

const LIST_ICON = `<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><circle cx="2.5" cy="4" r="1.3"/><circle cx="2.5" cy="8" r="1.3"/><circle cx="2.5" cy="12" r="1.3"/><path d="M6 4h8M6 8h8M6 12h8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>`;
const EMPTY_ICON = `<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>`;

/** Formatting buttons keep focus in the editor and apply the command to the selection. */
addEventListener("mousedown", (event) => {
  if (event.target.closest(".rich-toolbar button")) event.preventDefault();
});
addEventListener("click", (event) => {
  const button = event.target.closest(".rich-toolbar button");
  if (!button) return;
  button.closest(".rich-wrap").querySelector(".rich").focus();
  document.execCommand(button.dataset.cmd);
});

/** A friendly empty state. */
export function emptyHtml(message) {
  return `<div class="empty-state"><span class="empty-icon">${EMPTY_ICON}</span><p>${esc(message)}</p></div>`;
}

export async function options() {
  optionsCache ??= await fetch("/api/v2/options/").then((r) => r.json());
  return optionsCache;
}

function inputHtml(def, value) {
  const name = `data-field="${def.name}"`;
  switch (def.type) {
    case "select":
      return `<select ${name} ${def.integer ? 'data-kind="int"' : ""}><option value=""></option>${def.options
        .map((o) => {
          const [v, label] = Array.isArray(o) ? o : [o, o];
          return `<option value="${esc(v)}" ${String(v) === String(value) ? "selected" : ""}>${esc(label)}</option>`;
        }).join("")}</select>`;
    case "yesno":
      return `<select ${name} data-kind="yesno"><option value=""></option>
        <option value="true" ${value === true ? "selected" : ""}>Yes</option>
        <option value="false" ${value === false ? "selected" : ""}>No</option></select>`;
    case "multi":
      return `<div class="checks" ${name} data-kind="multi">${def.options.map((o) => `
        <label class="check"><input type="checkbox" value="${esc(o)}" ${(value ?? []).includes(o) ? "checked" : ""}>${esc(o)}</label>`).join("")}</div>`;
    case "rich":
      return `<div class="rich-wrap">
        <div class="rich-toolbar" role="toolbar" aria-label="Text formatting">
          <button type="button" data-cmd="bold" aria-label="Bold"><strong>B</strong></button>
          <button type="button" data-cmd="italic" aria-label="Italic"><em>I</em></button>
          <button type="button" data-cmd="insertUnorderedList" aria-label="Bulleted list">${LIST_ICON}</button>
        </div>
        <div class="rich" contenteditable="true" role="textbox" aria-multiline="true" ${name}>${value ?? ""}</div></div>`;
    case "checkbox":
      return `<input type="checkbox" ${name} ${value ? "checked" : ""}>`;
    case "goalmonth":
      return `<input type="month" ${name} data-kind="goalmonth" value="${esc(value ?? "")}">`;
    case "textarea":
      return `<textarea ${name} rows="3">${esc(value)}</textarea>`;
    case "month":
      return `<input type="month" ${name} value="${esc(value ? value.slice(0, 7) : "")}">`;
    default:
      return `<input type="${def.type || "text"}" ${name} value="${esc(value)}" ${def.step ? `step="${def.step}"` : ""}>`;
  }
}

export function fieldHtml(def, value) {
  const wide = def.wide || ["rich", "multi", "textarea"].includes(def.type) ? " wide" : "";
  return `<label class="field${wide}" data-wrap="${def.wrap ?? def.name}">
    <span>${esc(def.label)}</span>${inputHtml(def, value)}<small class="err"></small></label>`;
}

export function fieldsHtml(defs, values) {
  return `<div class="fields">${defs.map((d) => fieldHtml(d, values?.[d.name])).join("")}</div>`;
}

/** Read an input's value in the shape the API expects. */
export function readValue(el) {
  if (el.dataset.kind === "multi") return [...el.querySelectorAll("input:checked")].map((box) => box.value);
  if (el.dataset.kind === "goalmonth") return el.value ? `${el.value.slice(5, 7)}-${el.value.slice(0, 4)}` : null;
  if (el.dataset.kind === "int") return el.value === "" ? null : Number(el.value);
  if (el.dataset.kind === "yesno") return el.value === "" ? null : el.value === "true";
  if (el.isContentEditable) return el.innerHTML;
  if (el.type === "checkbox") return el.checked;
  if (el.type === "number") return el.value === "" ? null : Number(el.value);
  if (el.type === "month") return el.value ? `${el.value}-01` : null;
  return el.value;
}

/** Turn a 422 body into a message per field. */
export function errorMessages(err) {
  if (err.status !== 422 || typeof err.data?.detail === "string") return { _: err.data?.detail ?? "Save failed" };
  const messages = {};
  for (const e of err.data.detail) {
    messages[e.loc.at(-1) === "body" ? "_" : e.loc.at(-1)] = e.msg.replace(/^Value error, /, "");
  }
  return messages;
}

/** Find a field wrapper. Rows from different tables can share an id and rows can nest, so the field must belong to that exact row. */
function wrapFor(root, name, rowId) {
  if (!rowId) return root.querySelector(`[data-wrap="${name}"]:not([data-row-id] *)`);
  for (const row of root.querySelectorAll(`[data-row-id="${rowId}"]`)) {
    const wrap = [...row.querySelectorAll(`[data-wrap="${name}"]`)].find((w) => w.closest("[data-row-id]") === row);
    if (wrap) return wrap;
  }
  return null;
}

export function setWrapError(wrap, message, kind = "save") {
  wrap.querySelector(".err").textContent = message;
  wrap.classList.toggle("invalid", Boolean(message));
  wrap.dataset.errorKind = message ? kind : "";
}

export function setFieldError(root, name, rowId, message, kind = "save") {
  const wrap = wrapFor(root, name, rowId);
  if (!wrap) return false;
  setWrapError(wrap, message, kind);
  return true;
}

/** Briefly mark a field as saved. */
function flashSaved(wrap) {
  if (!wrap) return;
  wrap.classList.remove("just-saved");
  void wrap.offsetWidth;
  wrap.classList.add("just-saved");
}

/**
 * Call save({ name, value, rowId, el }) when an input changes (rich text on blur).
 * Shows 422 messages under the field and fires tp:saved on success.
 */
export function bindAutosave(root, save) {
  const handle = async (event) => {
    const el = event.target.closest("[data-field]");
    if (!el || !root.contains(el) || el.closest("[data-draft]")) return;
    const rowId = el.closest("[data-row-id]")?.dataset.rowId ?? null;
    const name = el.dataset.field;
    const wrap = el.closest("[data-wrap]");
    if (wrap) setWrapError(wrap, "");
    dispatchEvent(new Event("tp:saving"));
    try {
      await save({ name, value: readValue(el), rowId: rowId && Number(rowId), el });
      flashSaved(wrap);
      dispatchEvent(new Event("tp:saved"));
    } catch (err) {
      if (!err.status) throw err;
      const messages = errorMessages(err);
      if (wrap) setWrapError(wrap, messages[name] ?? messages._ ?? Object.values(messages)[0]);
      dispatchEvent(new Event("tp:invalid"));
    }
  };
  root.addEventListener("change", handle);
  root.addEventListener("focusout", (event) => event.target.isContentEditable && handle(event));
}

/** Show completion errors under matching fields, the rest in a summary. A data-error-scope element limits errors to fields with that prefix. */
export function showPageErrors(root, status) {
  root.querySelectorAll('[data-error-kind="completion"]').forEach((wrap) => {
    wrap.classList.remove("invalid");
    wrap.querySelector(".err").textContent = "";
  });
  const scope = root.querySelector("[data-error-scope]")?.dataset.errorScope;
  const errors = scope ? status.errors.filter((e) => e.field.startsWith(scope)) : status.errors;
  const leftover = errors.filter((e) => !setFieldError(root, e.field, e.row_id, e.message, "completion"));
  const summary = root.querySelector(".page-errors");
  if (summary) {
    summary.innerHTML = leftover.map((e) => `<li>${esc(e.message)}</li>`).join("");
    summary.hidden = !leftover.length;
  }
}

/** A list of editable rows, each with its fields, optional extra action buttons, and a delete link. defs may be a function of the row. */
export function rowListHtml(rows, defs, noun, actions = "") {
  const title = noun[0].toUpperCase() + noun.slice(1);
  const items = rows.map((row, i) => `
    <div class="row" data-row-id="${row.id}">
      <div class="row-title"><span class="row-number">${i + 1}</span>${esc(title)} ${i + 1}</div>
      ${fieldsHtml(typeof defs === "function" ? defs(row) : defs, row)}
      <div class="row-actions">${actions}<button type="button" class="link danger" data-delete-row="${row.id}">Delete ${esc(noun)}</button></div>
    </div>`).join("");
  return items || emptyHtml(`No ${noun} added yet.`);
}

/** Button that creates an empty row; wired by bindRowActions. */
export function addRowButton(noun) {
  return `<button type="button" data-add-row>Add ${esc(noun)}</button>`;
}

/** Wire add and delete buttons from rowListHtml. Calls refresh() after each change. */
export function bindRowActions(root, { add, remove, refresh, noun }) {
  root.addEventListener("click", async (event) => {
    if (event.target.matches("[data-add-row]")) {
      await add();
    } else if (event.target.matches("[data-delete-row]")) {
      if (!confirm(`Delete this ${noun}?`)) return;
      await remove(event.target.dataset.deleteRow);
    } else {
      return;
    }
    await refresh();
  });
}

/** A new-row form whose fields are saved together by one button. */
export function draftHtml(defs, noun) {
  return `<div class="row draft" data-draft hidden>
      <h3>New ${esc(noun)}</h3>
      ${fieldsHtml(defs, {})}
      <small class="err" data-draft-error></small>
      <div class="actions"><button type="button" data-draft-save>Save ${esc(noun)}</button>
      <button type="button" class="link" data-draft-cancel>Cancel</button></div>
    </div>
    <button type="button" data-draft-open>Add ${esc(noun)}</button>`;
}

/** Wire the draft form: open, cancel, and save via post(values). Calls refresh() after a save. */
export function bindDraft(root, { post, refresh, beforeOpen }) {
  const draft = root.querySelector("[data-draft]");
  root.addEventListener("click", async (event) => {
    if (event.target.matches("[data-draft-open]")) {
      if (beforeOpen) {
        await beforeOpen();
        dispatchEvent(new Event("tp:saved"));
      }
      draft.hidden = false;
      event.target.hidden = true;
    } else if (event.target.matches("[data-draft-cancel]")) {
      draft.hidden = true;
      root.querySelector("[data-draft-open]").hidden = false;
    } else if (event.target.matches("[data-draft-save]")) {
      const values = {};
      draft.querySelectorAll("[data-field]").forEach((el) => { values[el.dataset.field] = readValue(el); });
      draft.querySelectorAll("[data-wrap]").forEach((wrap) => setFieldError(draft, wrap.dataset.wrap, null, ""));
      draft.querySelector("[data-draft-error]").textContent = "";
      try {
        await post(values);
      } catch (err) {
        if (!err.status) throw err;
        for (const [name, message] of Object.entries(errorMessages(err))) {
          if (!setFieldError(draft, name, null, message)) draft.querySelector("[data-draft-error]").textContent = message;
        }
        return;
      }
      await refresh();
    }
  });
}

/** A labelled group of pill checkboxes. selected is a list of { id, value }. */
export function chipGroupHtml(type, label, groupOptions, selected) {
  const chosen = new Map(selected.map((s) => [s.value, s.id]));
  const boxes = groupOptions.map((value) => `
    <label class="check"><input type="checkbox" data-group="${type}" data-value="${esc(value)}"
      ${chosen.has(value) ? `checked data-id="${chosen.get(value)}"` : ""}>${esc(value)}</label>`).join("");
  return `<div class="group" data-wrap="${type}"><span>${esc(label)}</span><div class="checks">${boxes}</div><small class="err"></small></div>`;
}

/** Save chip changes: add(type, value) returns the created item, remove(type, id) deletes it. */
export function bindChips(root, { add, remove }) {
  root.addEventListener("change", async (event) => {
    const box = event.target.closest("[data-group]");
    if (!box) return;
    dispatchEvent(new Event("tp:saving"));
    try {
      if (box.checked) {
        box.dataset.id = (await add(box.dataset.group, box.dataset.value)).id;
      } else {
        await remove(box.dataset.group, box.dataset.id);
      }
    } catch (err) {
      if (!err.status) throw err;
      box.checked = !box.checked;
      setFieldError(root, box.dataset.group, null, errorMessages(err)._ ?? "Not saved");
      dispatchEvent(new Event("tp:invalid"));
      return;
    }
    dispatchEvent(new Event("tp:saved"));
  });
}
