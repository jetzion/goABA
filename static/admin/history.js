/** Admin - Change history: who changed what and when. Read only. */

import { adminApi } from "../api.js";
import { KEY_LABELS } from "../labels.js";
import { card, esc } from "../ui.js";

const WHEN = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });
const HINT = "Changes to roles, access, users, goal names, clients, providers, assignments and plans (created, copied, signed). Plan page content is not listed.";

let filter = "";

export async function render(root) {
  const data = await load();
  root.innerHTML = card("Change history", `
    <label class="field history-filter"><span>Show</span><select data-filter>
      <option value="">All changes</option>
      ${data.record_types.map((t) => `<option value="${esc(t)}" ${t === filter ? "selected" : ""}>${esc(capital(t))}</option>`).join("")}
    </select></label>
    <ol class="history-list">${data.events.map(eventHtml).join("") || `<li class="empty-note">No changes recorded yet.</li>`}</ol>
    <button type="button" class="secondary" data-older ${data.more ? "" : "hidden"}>Load older</button>`, HINT);
  let oldest = data.events.at(-1)?.id;

  root.querySelector("[data-filter]").addEventListener("change", async (event) => {
    filter = event.target.value;
    await render(root);
  });
  root.querySelector("[data-older]").addEventListener("click", async (event) => {
    const more = await load(oldest);
    root.querySelector(".history-list").insertAdjacentHTML("beforeend", more.events.map(eventHtml).join(""));
    oldest = more.events.at(-1)?.id ?? oldest;
    event.target.hidden = !more.more;
  });
}

function load(before) {
  const params = new URLSearchParams();
  if (filter) params.set("record_type", filter);
  if (before) params.set("before", before);
  return adminApi.get(`/history/?${params}`);
}

function capital(text) {
  return text[0].toUpperCase() + text.slice(1);
}

function shown(value) {
  if (value === null) return `<span class="muted">empty</span>`;
  if (typeof value === "boolean") return value ? "on" : "off";
  return esc(String(value));
}

function eventHtml(e) {
  const fields = Object.entries(e.changes).map(([field, [old, now]]) => {
    const name = esc(capital(field.replaceAll("_", " ")));
    if (e.action === "deleted") return `<li><span>${name}</span> was ${shown(old)}</li>`;
    if (old === null) return `<li><span>${name}</span> ${shown(now)}</li>`;
    return `<li><span>${name}</span> ${shown(old)} → ${shown(now)}</li>`;
  }).join("");
  return `<li class="history-item">
    <div class="history-head">
      <span class="history-action is-${esc(e.action)}">${esc(capital(e.action))}</span>
      <strong>${esc(capital(e.record_type))}: ${esc(readable(e))}</strong>
      <span class="history-meta">${esc(e.user_name)} · <time datetime="${esc(e.at)}">${WHEN.format(new Date(e.at))}</time></span>
    </div>
    ${fields ? `<ul class="history-changes">${fields}</ul>` : ""}
  </li>`;
}

/** Access entries are labeled "Role: key"; show the key as the matrix names it. */
function readable(e) {
  if (e.record_type !== "access") return e.label;
  const at = e.label.lastIndexOf(": ");
  const key = e.label.slice(at + 2);
  return `${e.label.slice(0, at)}: ${KEY_LABELS[key] ?? key}`;
}
