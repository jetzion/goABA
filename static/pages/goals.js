/** Goals page: parent caregiver, skill acquisition and behavior reduction goals, with targets and stages. */

import { api } from "../api.js";
import { bindAutosave, bindDraft, draftHtml, emptyHtml, fieldsHtml, options } from "../form.js";
import { esc, rerender } from "../ui.js";

const SECTIONS = {
  pcg: { title: "Parent caregiver", blocks: ["mastery"], opportunities: true, responses: true, frequency: false,
    hint: "Goals for the parent or caregiver, in the Parent training focus area." },
  sag: { title: "Skill acquisition", blocks: ["acquisition", "generalization", "maintenance"], opportunities: true, responses: true, frequency: true,
    hint: "Skills for the client. Each goal has acquisition, generalization and maintenance criteria." },
  brg: { title: "Behavior reduction", blocks: ["mastery"], opportunities: false, responses: false, frequency: true,
    hint: "Behaviors to reduce. Each goal links to a DSM-5 symptom from the Assessment page." },
};
const BRG_TEXT = [
  ["operational_definition", "Operational definition"],
  ["objective", "Objective"],
  ["antecedent_modifications", "Antecedent modifications"],
  ["consequence_modifications", "Consequence modifications"],
];
const BLOCK_PARTS = {
  Duration: ["direction", "aggregation", "to", "sessions"],
  Instances: ["direction", "to", "sessions"],
  Percentage: ["responses", "sessions"],
  Rate: ["direction", "to", "sessions"],
};
const METHOD_FIELDS = { Duration: ["duration_unit"], Instances: [], Percentage: ["opportunities"], Rate: ["rate_interval", "rate_unit"] };
const titleCase = (s) => s[0].toUpperCase() + s.slice(1);

let current = "pcg";
try { current = localStorage.getItem("tp.goals.section") ?? "pcg"; } catch { /* storage unavailable */ }

function fieldDef(o, name, label) {
  const selects = {
    duration_unit: o.MEASUREMENT_UNITS, rate_unit: o.MEASUREMENT_UNITS, timeframe: o.TARGET_TIMEFRAMES,
    frequency: o.GOAL_FREQUENCIES, direction: o.MASTERY_DIRECTIONS, aggregation: o.DURATION_AGGREGATIONS,
  };
  const base = name.split("_").at(-1);
  if (selects[name] || selects[base]) return { name, label, type: "select", options: selects[name] ?? selects[base] };
  if (/(level|opportunities|interval|_to|responses|sessions)$/.test(name)) return { name, label, type: "number" };
  return { name, label };
}

function scoped(sec, row, defs) {
  return defs.map((d) => ({ ...d, wrap: `${sec}.${row}.${d.name}` }));
}

function methodDefs(o, sec, method, forTarget) {
  const names = (METHOD_FIELDS[method] ?? []).filter((n) => n !== "opportunities" || SECTIONS[sec].opportunities);
  const labels = { duration_unit: "Duration unit", opportunities: "Opportunities", rate_interval: "Rate interval", rate_unit: "Rate unit" };
  return scoped(sec, forTarget ? "target" : "goal", names.map((n) => fieldDef(o, n, labels[n])));
}

function criteriaHtml(o, sec, goal) {
  const method = goal.data_collection_method;
  if (!method) return "";
  const labels = { direction: "Direction", aggregation: "Aggregation", to: "Target value", responses: "Responses", sessions: "Sessions" };
  return SECTIONS[sec].blocks.map((block) => {
    const parts = BLOCK_PARTS[method].filter((p) => p !== "responses" || SECTIONS[sec].responses);
    const defs = scoped(sec, "goal", parts.map((p) => fieldDef(o, `${block}_${p}`, labels[p])));
    return `<div class="criteria"><h4>${titleCase(block)} criteria</h4>${fieldsHtml(defs, goal)}</div>`;
  }).join("");
}

function stagesHtml(sec, target) {
  const today = new Date().toISOString().slice(0, 10);
  const timeline = target.stage_history.map((s, i) => `
    <li class="stage ${i === target.stage_history.length - 1 ? "current" : ""}" data-stage="${esc(s.stage)}">
      <span class="stage-name">${esc(s.stage)}</span><span class="stage-date">${esc(s.stage_date)}</span>
      ${s.reason ? `<span class="stage-reason">${esc(s.reason)}</span>` : ""}</li>`).join("");
  const move = target.allowed_next_stages.length ? `
    <div class="move" data-move="${target.id}">
      <label><span>Move to</span><select data-move-stage>${target.allowed_next_stages.map((s) => `<option>${esc(s)}</option>`).join("")}</select></label>
      <label><span>Date</span><input type="date" data-move-date value="${today}"></label>
      <label class="grow"><span>Reason (optional)</span><input type="text" maxlength="500" data-move-reason></label>
      <button type="button" data-move-save>Move</button>
    </div><small class="err" data-move-error></small>` : '<p class="muted">No further moves from this stage.</p>';
  const undo = target.stage_history.length > 1
    ? `<button type="button" class="link" data-undo-stage="${target.stage_history.at(-1).id}">Undo last move</button>` : "";
  return `<div class="stages field" data-wrap="${sec}.target.stage_history">
    <h4>Stage history</h4><ol class="timeline">${timeline}</ol>${move}<small class="err"></small></div>${undo}`;
}

function targetHtml(o, sec, goal, t) {
  const defs = [
    ...scoped(sec, "target", [
      { name: "target_name", label: "Target name" },
      fieldDef(o, "timeframe", "Target timeframe"),
      { name: "baseline_date", label: "Baseline date", type: "date" },
      fieldDef(o, "baseline_level", "Baseline level"),
    ]),
    ...methodDefs(o, sec, goal.data_collection_method, true),
    ...scoped(sec, "target", [
      { name: "description", label: "Description", type: "rich" },
      { name: "instructions", label: "Instructions", type: "textarea" },
    ]),
  ];
  return `<div class="row target" data-row-id="${t.id}" data-target-id="${t.id}">
    <div class="target-head"><span class="stage-badge" data-stage="${esc(t.current_stage)}">${esc(t.current_stage)}</span></div>
    ${fieldsHtml(defs, t)}
    ${stagesHtml(sec, t)}
    <div class="row-actions"><button type="button" class="link danger" data-delete-target="${t.id}">Delete target</button></div>
  </div>`;
}

function brgExtrasHtml(o, data, goal) {
  const links = data.sag_goals.length
    ? `<div class="checks">${data.sag_goals.map((s) => `<label class="check"><input type="checkbox" data-link-sag value="${s.id}"
        ${goal.linked_sag_goal_ids.includes(s.id) ? "checked" : ""}>${esc(s.goal_name)}</label>`).join("")}</div>`
    : '<p class="muted">No skill acquisition goals on this plan yet.</p>';
  const entries = goal.hypothesized_functions.map((f) => `<li><span class="stage-date">${esc(f.function_date)}</span>
    <span>${f.functions.map(esc).join(", ")}</span><button type="button" class="link danger" data-delete-fn="${f.id}">Remove</button></li>`).join("");
  return `
    <div class="extra"><h4>Linked skill acquisition goals</h4>${links}</div>
    <div class="extra field" data-wrap="brg.goal.hypothesized_functions"><h4>Hypothesized functions</h4>
      <ul class="fn-list">${entries}</ul>
      <div class="fn-add"><input type="date" data-fn-date aria-label="Function date">
        <div class="checks">${o.HYPOTHESIZED_FUNCTIONS.map((f) => `<label class="check"><input type="checkbox" data-fn-value value="${esc(f)}">${esc(f)}</label>`).join("")}</div>
        <button type="button" data-add-fn>Add entry</button></div>
      <small class="err"></small></div>`;
}

function goalHtml(o, sec, data, goal) {
  const s = SECTIONS[sec];
  const methods = sec === "brg" ? o.DATA_COLLECTION_METHODS.filter((m) => m !== "Percentage") : o.DATA_COLLECTION_METHODS;
  const main = scoped(sec, "goal", [
    { name: "data_collection_method", label: "Data collection method", type: "select", options: methods },
    ...(sec === "brg" ? [{ name: "dsm5_symptom", label: "DSM-5 symptom", type: "select", wide: true, options: data.dsm5_symptoms.map((x) => [x, x.split(",")[0]]) }] : []),
    { name: "baseline_date", label: "Baseline date", type: "date" },
    fieldDef(o, "baseline_level", "Baseline level"),
    fieldDef(o, "current_level", "Current level"),
    { name: "expected_mastery_date", label: "Expected mastery", type: "goalmonth" },
    ...(s.frequency ? [fieldDef(o, "frequency", "Frequency")] : []),
  ]);
  const texts = scoped(sec, "goal", [
    { name: "goal_description", label: "Goal description", type: "rich" },
    ...(sec === "brg" ? BRG_TEXT.map(([name, label]) => ({ name, label, type: "rich" })) : []),
  ]);
  return `<article class="goal" data-row-id="${goal.id}" data-goal-id="${goal.id}">
    <header class="goal-head"><span class="prefix">${esc(goal.prefix)}</span><h3>${esc(goal.goal_name)}</h3>
      <button type="button" class="link danger" data-delete-goal="${goal.id}">Delete goal</button></header>
    ${fieldsHtml([...main, ...methodDefs(o, sec, goal.data_collection_method, false)], goal)}
    ${criteriaHtml(o, sec, goal)}
    ${fieldsHtml(texts, goal)}
    ${sec === "brg" ? brgExtrasHtml(o, data, goal) : ""}
    <div class="targets"><h4>Targets</h4>
      ${goal.targets.map((t) => targetHtml(o, sec, goal, t)).join("") || emptyHtml("No target added yet.")}
      <button type="button" class="secondary" data-add-target="${goal.id}">Add target</button></div>
  </article>`;
}

function goalNameOptions(sec, data) {
  const used = new Set(data.goals.map((g) => g.goal_name_id));
  const all = sec === "pcg"
    ? data.available_goals.map((g) => [g.id, `${g.prefix} ${g.label}`])
    : data.focus_areas.flatMap((a) => a.goals.map((g) => [g.id, `${sec === "sag" ? `${a.name}: ` : ""}${g.prefix} ${g.label}`]));
  return all.filter(([id]) => !used.has(id));
}

function tabCounts(status) {
  const counts = { pcg: 0, sag: 0, brg: 0 };
  for (const e of status?.errors ?? []) counts[e.field.split(".")[0]] += 1;
  return counts;
}

function tabsHtml(counts) {
  return `<div class="tabs" role="tablist">${Object.entries(SECTIONS).map(([key, s]) => `
    <button type="button" role="tab" class="tab" data-tab="${key}" aria-selected="${key === current}">
      ${esc(s.title)}<span class="tab-count" data-count="${key}" ${counts[key] ? "" : "hidden"}>${counts[key]}</span></button>`).join("")}</div>`;
}

export async function render(container, planId) {
  const o = await options();
  const base = `/${planId}/pages/${current}/`;
  const [data, statuses] = await Promise.all([api.get(base), api.get(`/${planId}/pages/`)]);
  const status = statuses.find((s) => s.page === "goals");
  const s = SECTIONS[current];
  const nameOptions = goalNameOptions(current, data);
  const methods = current === "brg" ? o.DATA_COLLECTION_METHODS.filter((m) => m !== "Percentage") : o.DATA_COLLECTION_METHODS;

  container.innerHTML = `
    ${tabsHtml(tabCounts(status))}
    <div data-error-scope="${current}.">
      <p class="section-intro">${esc(s.hint)}</p>
      <ul class="page-errors" hidden></ul>
      ${data.goals.map((g) => goalHtml(o, current, data, g)).join("") || emptyHtml(`No ${s.title.toLowerCase()} goal added yet.`)}
      ${nameOptions.length ? draftHtml([
        { name: "goal_name_id", label: "Goal", type: "select", integer: true, options: nameOptions },
        { name: "data_collection_method", label: "Data collection method", type: "select", options: methods },
      ], "goal") : '<p class="muted">Every goal in this focus area is already on the plan.</p>'}
    </div>`;

  const refresh = () => rerender(container, render, planId);
  const goalUrl = (el) => `${base}goals/${el.closest("[data-goal-id]").dataset.goalId}/`;

  bindAutosave(container, async ({ name, value, el }) => {
    const target = el.closest("[data-target-id]");
    if (target) return api.patch(`${goalUrl(el)}targets/${target.dataset.targetId}/`, { [name]: value });
    await api.patch(goalUrl(el), { [name]: value });
    if (name === "data_collection_method") await refresh();
  });
  bindDraft(container, { post: (values) => api.post(`${base}goals/`, values), refresh });

  const updateCounts = async () => {
    if (!container.isConnected) return removeEventListener("tp:saved", updateCounts);
    const fresh = (await api.get(`/${planId}/pages/`)).find((x) => x.page === "goals");
    for (const [key, n] of Object.entries(tabCounts(fresh))) {
      const badge = container.querySelector(`[data-count="${key}"]`);
      badge.textContent = n;
      badge.hidden = !n;
    }
  };
  addEventListener("tp:saved", updateCounts);

  container.addEventListener("click", async (event) => {
    const t = event.target;
    if (t.dataset.tab) {
      current = t.dataset.tab;
      try { localStorage.setItem("tp.goals.section", current); } catch { /* storage unavailable */ }
      return refresh();
    }
    if (t.dataset.deleteGoal) {
      if (!confirm("Delete this goal and its targets?")) return;
      await api.del(goalUrl(t));
    } else if (t.dataset.addTarget) {
      await api.post(`${goalUrl(t)}targets/`, {});
    } else if (t.dataset.deleteTarget) {
      if (!confirm("Delete this target?")) return;
      await api.del(`${goalUrl(t)}targets/${t.dataset.deleteTarget}/`);
    } else if (t.matches("[data-move-save]")) {
      const move = t.closest("[data-move]");
      const body = {
        stage: move.querySelector("[data-move-stage]").value,
        stage_date: move.querySelector("[data-move-date]").value,
        reason: move.querySelector("[data-move-reason]").value || null,
      };
      try {
        await api.post(`${goalUrl(t)}targets/${move.dataset.move}/stage-history/`, body);
      } catch (err) {
        if (err.status !== 422) throw err;
        move.nextElementSibling.textContent = typeof err.data.detail === "string" ? err.data.detail : "Choose a valid date";
        return;
      }
    } else if (t.dataset.undoStage) {
      const targetId = t.closest("[data-target-id]").dataset.targetId;
      await api.del(`${goalUrl(t)}targets/${targetId}/stage-history/${t.dataset.undoStage}/`);
    } else if (t.matches("[data-add-fn]")) {
      const add = t.closest(".fn-add");
      const functions = [...add.querySelectorAll("[data-fn-value]:checked")].map((b) => b.value);
      try {
        await api.post(`${goalUrl(t)}hypothesized-functions/`, { function_date: add.querySelector("[data-fn-date]").value || null, functions });
      } catch (err) {
        if (err.status !== 422 && err.status !== 409) throw err;
        const wrap = t.closest("[data-wrap]");
        wrap.classList.add("invalid");
        wrap.querySelector(".err").textContent = err.status === 409 ? err.data.detail : "Pick a date and one to four functions";
        return;
      }
    } else if (t.dataset.deleteFn) {
      await api.del(`${goalUrl(t)}hypothesized-functions/${t.dataset.deleteFn}/`);
    } else {
      return;
    }
    await refresh();
  });

  container.addEventListener("change", async (event) => {
    if (!event.target.matches("[data-link-sag]")) return;
    const article = event.target.closest("[data-goal-id]");
    const ids = [...article.querySelectorAll("[data-link-sag]:checked")].map((b) => Number(b.value));
    dispatchEvent(new Event("tp:saving"));
    await api.patch(goalUrl(event.target), { linked_sag_goal_ids: ids });
    dispatchEvent(new Event("tp:saved"));
  });
}
