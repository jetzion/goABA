/** Child page: background lists, other behavior issues, and the weekly ABA schedule. */

import { api } from "../api.js";
import { bindAutosave, bindChips, bindDraft, chipGroupHtml, draftHtml, emptyHtml, errorMessages, fieldsHtml, options, setFieldError } from "../form.js";
import { card, esc, rerender } from "../ui.js";

const CHIP_TYPES = [
  ["COMMUNICATION_STYLE", "Child communication style", "COMMUNICATION_STYLES"],
  ["GOALS_FOR_THERAPY", "Goals for therapy", "THERAPY_GOALS"],
  ["BEHAVIOR_ISSUE", "Child's behavior issues", "BEHAVIOR_ISSUES"],
];
const TEXT_TYPES = [
  ["STRENGTH", "Child's strengths"],
  ["WEAKNESS", "Child's weaknesses"],
  ["INTEREST", "Child's interests"],
  ["DISLIKES", "Child's dislikes"],
];
const titleCase = (day) => day[0] + day.slice(1).toLowerCase();

/** Free-text entries: an add field, then the entries as removable bubbles that wrap onto new lines. */
function textList([type, label], items) {
  const bubbles = items.map((i) => `<li class="bubble">
    <button type="button" class="bubble-remove" data-remove-item="${i.id}" aria-label="Remove ${esc(i.background_description)}">&times;</button>
    <span>${esc(i.background_description)}</span></li>`).join("");
  return `<div class="group text-list" data-wrap="${type}">
    <span>${esc(label)} (at least 2)</span>
    <div class="add-item"><input type="text" data-new-item="${type}" placeholder="Add one" maxlength="2000" aria-label="${esc(label)}">
      <button type="button" data-add-item="${type}">Add</button></div>
    ${items.length ? `<ul class="bubbles">${bubbles}</ul>` : ""}
    <small class="err"></small></div>`;
}

function scheduleList(slots, activities) {
  if (!slots.length) return emptyHtml("No time slot added yet.");
  return `<ul class="slots">${slots.map((s) => `
    <li data-activity="${s.schedule_activity_type}">
      <span class="slot-day">${titleCase(s.day_of_week)}</span>
      <span class="slot-time">${s.schedule_start_date.slice(11, 16)} to ${s.schedule_end_date.slice(11, 16)}</span>
      <span class="slot-activity">${esc(activities[s.schedule_activity_type])}</span>
      <button type="button" class="link danger" data-remove-slot="${s.id}">Remove</button>
    </li>`).join("")}</ul>`;
}

/** Build an ISO datetime for a local time today, with the browser's current UTC offset. */
function localDateTime(timeValue) {
  const offsetMinutes = -new Date().getTimezoneOffset();
  const sign = offsetMinutes < 0 ? "-" : "+";
  const abs = Math.abs(offsetMinutes);
  const pad = (n) => String(n).padStart(2, "0");
  const today = new Date();
  const date = `${today.getFullYear()}-${pad(today.getMonth() + 1)}-${pad(today.getDate())}`;
  return { iso: `${date}T${timeValue}:00${sign}${pad(Math.floor(abs / 60))}:${pad(abs % 60)}`, seconds: offsetMinutes * 60 };
}

export async function render(container, planId) {
  const o = await options();
  const base = `/${planId}/pages/child/`;
  const data = await api.get(base);
  const ofType = (type) => data.backgrounds.filter((b) => b.background_type === type);
  const slotDefs = [
    { name: "day_of_week", label: "Day of week", type: "select", options: o.DAYS_OF_WEEK.map((d) => [d, titleCase(d)]) },
    { name: "schedule_activity_type", label: "Activity", type: "select", options: Object.entries(o.SCHEDULE_ACTIVITIES) },
    { name: "start_time", label: "Start time", type: "time" },
    { name: "end_time", label: "End time", type: "time" },
  ];

  container.innerHTML = `
    <ul class="page-errors" hidden></ul>
    ${card("Communication and goals", CHIP_TYPES.slice(0, 2).map(([t, l, k]) =>
      chipGroupHtml(t, l, o[k], ofType(t).map((b) => ({ id: b.id, value: b.background_description })))).join(""),
      "Pick at least one in each group.")}
    ${card("Strengths and interests", TEXT_TYPES.map((t) => textList(t, ofType(t[0]))).join(""),
      "In the family's words. Add at least two of each.")}
    ${card("Behavior", chipGroupHtml(...CHIP_TYPES[2].slice(0, 2), o.BEHAVIOR_ISSUES,
      ofType("BEHAVIOR_ISSUE").map((b) => ({ id: b.id, value: b.background_description }))) +
      fieldsHtml([{ name: "child_behavior_issues", label: "Any other child behavior issues", type: "rich" }], data),
      "Pick at least one. The notes below are optional.")}
    ${card("ABA therapy schedule availability", `
      <div class="field" data-wrap="schedule"><small class="err"></small></div>
      ${scheduleList(data.schedule, o.SCHEDULE_ACTIVITIES)}
      ${draftHtml(slotDefs, "time slot")}`,
      "Weekly availability. Slots on the same day cannot overlap.")}`;

  const refresh = () => rerender(container, render, planId);

  bindAutosave(container, ({ name, value }) => api.patch(base, { [name]: value }));
  bindChips(container, {
    add: (type, value) => api.post(`${base}backgrounds/`, { background_type: type, background_description: value }),
    remove: (_type, id) => api.del(`${base}backgrounds/${id}/`),
  });
  bindDraft(container, {
    post: (v) => {
      const start = localDateTime(v.start_time);
      const end = localDateTime(v.end_time);
      return api.post(`${base}schedule/`, {
        day_of_week: v.day_of_week,
        schedule_activity_type: v.schedule_activity_type,
        schedule_start_date: v.start_time ? start.iso : null,
        schedule_end_date: v.end_time ? end.iso : null,
        utc_offset: start.seconds,
      });
    },
    refresh,
  });

  container.addEventListener("click", async (event) => {
    const addType = event.target.dataset.addItem;
    const removeId = event.target.dataset.removeItem ?? event.target.dataset.removeSlot;
    if (addType) {
      const input = container.querySelector(`[data-new-item="${addType}"]`);
      try {
        await api.post(`${base}backgrounds/`, { background_type: addType, background_description: input.value });
      } catch (err) {
        if (!err.status) throw err;
        const messages = errorMessages(err);
        setFieldError(container, addType, null, messages.background_description ?? messages._ ?? "Not saved");
        return;
      }
      await refresh();
      document.querySelector(`[data-new-item="${addType}"]`)?.focus();
    } else if (removeId) {
      const path = event.target.dataset.removeSlot ? "schedule" : "backgrounds";
      await api.del(`${base}${path}/${removeId}/`);
      await refresh();
    }
  });
  container.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && event.target.dataset.newItem) {
      event.preventDefault();
      container.querySelector(`[data-add-item="${event.target.dataset.newItem}"]`).click();
    }
  });
}
