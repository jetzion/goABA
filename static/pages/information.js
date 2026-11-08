/** Information page: read-only client, insurance and care team. */

import { api } from "../api.js";
import { card, dl, esc } from "../ui.js";

function people(title, list, emptyMessage) {
  const body = list.length
    ? `<ul class="people">${list.map((p) => `<li><span>${esc(p.name)}</span><span class="muted">${esc(p.role)}</span></li>`).join("")}</ul>`
    : `<p class="muted">${esc(emptyMessage)}</p>`;
  return `<div class="tile"><h3>${esc(title)}</h3>${body}</div>`;
}

function policy(label, p) {
  const body = p
    ? dl([["Name", p.payor_name], ["Member ID", p.member_id], ["Start date", p.date_start], ["End date", p.date_end]])
    : `<p class="muted">No policy on file.</p>`;
  return `<div class="tile"><h3>${esc(label)}</h3>${body}</div>`;
}

export async function render(container, planId) {
  const data = await api.get(`/${planId}/pages/information/`);
  const c = data.client;
  const bcbas = [
    data.home_bcba && { name: data.home_bcba.display_name, role: "Home BCBA" },
    ...data.substitute_bcbas.map((p) => ({ name: p.display_name, role: "Substitute BCBA" })),
  ].filter(Boolean);

  container.innerHTML = `
    ${card("Client", dl([
      ["Name", `${c.first_name} ${c.last_name}`],
      ["Date of birth", c.date_of_birth],
      ["Gender", c.sex],
      ["Client ID", c.id],
    ]), "From the client record. Edit it there.")}
    ${card("Insurance", `<div class="tiles">
      ${policy("Primary", data.insurance.primary)}
      ${policy("Secondary", data.insurance.secondary)}
    </div>`)}
    ${card("Care team", `<div class="tiles">
      ${people("Parent/guardian", data.parents_guardians.map((g) => ({ name: g.display_name, role: g.role })), "No parents or guardians assigned.")}
      ${people("BT(s)", data.assigned_bts.map((p) => ({ name: p.display_name, role: "BT" })), "No BTs assigned.")}
      ${people("BCBA(s)", bcbas, "No BCBAs assigned.")}
    </div>`)}`;
}
