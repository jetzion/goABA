/** Referral page: repeatable referral rows. */

import { api } from "../api.js";
import { addRowButton, bindAutosave, bindRowActions, emptyHtml, options, rowListHtml } from "../form.js";
import { card, rerender } from "../ui.js";

export async function render(container, planId) {
  const o = await options();
  const defs = [
    { name: "referral_date", label: "Date", type: "date" },
    { name: "provider_name", label: "Provider name" },
    { name: "diagnosis_tool", label: "Diagnosis tool", type: "select", options: o.DIAGNOSIS_TOOLS },
    { name: "city", label: "City" },
    { name: "state", label: "State", type: "select", options: o.US_STATES },
  ];
  const base = `/${planId}/pages/referrals/`;
  const rows = await api.get(base);

  container.innerHTML = `
    <ul class="page-errors" hidden></ul>
    ${card("Referrals", `${rows.length ? rowListHtml(rows, defs, "referral") : emptyHtml("Add at least one referral.")}${addRowButton("referral")}`,
      "Each referral needs a date, provider, diagnosis tool, city and state.")}`;

  bindAutosave(container, ({ name, value, rowId }) => api.patch(`${base}${rowId}/`, { [name]: value }));
  bindRowActions(container, {
    noun: "referral",
    add: () => api.post(base, {}),
    remove: (id) => api.del(`${base}${id}/`),
    refresh: () => rerender(container, render, planId),
  });
}
