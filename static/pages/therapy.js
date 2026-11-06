/** Therapy page: no-historical-therapy checkbox, therapy rows, and a draft form for new rows. */

import { api } from "../api.js";
import { bindAutosave, bindDraft, bindRowActions, draftHtml, options, rowListHtml } from "../form.js";
import { card, rerender } from "../ui.js";

function defs(o) {
  return [
    { name: "provider_name", label: "Provider name" },
    { name: "service_type", label: "Service type", type: "select", options: o.THERAPY_SERVICE_TYPES },
    { name: "phone_number", label: "Phone number", type: "tel" },
    { name: "email", label: "Email", type: "email" },
    { name: "start_date", label: "Start month", type: "month" },
    { name: "end_date", label: "End month", type: "month" },
    { name: "hours", label: "Hours", type: "number", step: "0.1" },
    { name: "frequency", label: "Service frequency", type: "select", options: o.THERAPY_FREQUENCIES },
    { name: "progress", label: "Progress", type: "select", options: o.THERAPY_PROGRESS },
    { name: "is_record_shared", label: "Record shared", type: "select", options: o.RECORD_SHARED },
    { name: "do_not_share_info_with_provider", label: "Do not share info with provider", type: "checkbox" },
  ];
}

/** Checking do-not-share also clears record shared, which must then be empty. */
function rowPatch(name, value) {
  if (name === "do_not_share_info_with_provider" && value) return { [name]: value, is_record_shared: null };
  return { [name]: value };
}

export async function render(container, planId) {
  const fields = defs(await options());
  const base = `/${planId}/pages/therapy/`;
  const data = await api.get(base);
  const rows = data.therapies;
  const flag = data.no_historical_therapy;

  container.innerHTML = `
    <ul class="page-errors" hidden></ul>
    <div class="field" data-wrap="no_historical_therapy">
      <label class="flag"><input type="checkbox" data-flag ${flag ? "checked" : ""}> No historical therapy</label>
      <small class="err"></small>
    </div>
    ${flag ? "" : card("Historical therapy", rowListHtml(rows, fields, "therapy") + draftHtml(fields, "therapy"), "Therapy the client received before this plan. End month is optional.")}`;

  const refresh = () => rerender(container, render, planId);

  container.querySelector("[data-flag]").addEventListener("change", async (event) => {
    if (event.target.checked && rows.length) {
      if (!confirm("Checking this deletes every therapy on this page. Continue?")) {
        event.target.checked = false;
        return;
      }
      for (const row of rows) await api.del(`${base}${row.id}/`);
    }
    await api.patch(base, { no_historical_therapy: event.target.checked });
    await refresh();
  });

  if (flag) return;

  bindAutosave(container, async ({ name, value, rowId }) => {
    await api.patch(`${base}${rowId}/`, rowPatch(name, value));
    if (name === "do_not_share_info_with_provider") await refresh();
  });
  bindRowActions(container, { noun: "therapy", remove: (id) => api.del(`${base}${id}/`), refresh });
  bindDraft(container, {
    beforeOpen: () => flag === null && api.patch(base, { no_historical_therapy: false }),
    post: (values) => api.post(base, { ...values, ...(values.do_not_share_info_with_provider ? { is_record_shared: null } : {}) }),
    refresh,
  });
}
