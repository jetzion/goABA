/** Assessment page: info, maladaptive behaviors, summary, methods with visuals, barriers, observations, telehealth. */

import { api } from "../api.js";
import { addRowButton, bindAutosave, bindRowActions, emptyHtml, fieldsHtml, options, rowListHtml } from "../form.js";
import { card, esc, rerender } from "../ui.js";

const SECTION_LABELS = { child: "Child", caregiver: "Caregiver", environment: "Environment" };

function defs(o) {
  return {
    info: [
      { name: "initial_assessment_date", label: "Initial assessment date", type: "date" },
      { name: "reassessment_date", label: "Re-assessment date", type: "date" },
      { name: "diagnostic_report_reviewed", label: "Was diagnostic report reviewed", type: "yesno" },
      { name: "parent_interview_summary", label: "Parent interview summary", type: "rich" },
      { name: "additional_files_viewed", label: "Additional files viewed", type: "multi", options: o.ADDITIONAL_FILES },
    ],
    behavior: [
      { name: "dsm5_symptom", label: "Respective DSM5 symptoms", type: "select", wide: true, options: o.DSM5_SYMPTOMS.map((s) => [s, s.split(",")[0].split(" (")[0]]) },
      { name: "behavior", label: "Maladaptive behavior", type: "rich" },
      { name: "parent_concerns", label: "Maladaptive concerns as reported by parents", type: "rich" },
    ],
    method: [
      { name: "tool", label: "Tool used", type: "select", options: o.ASSESSMENT_TOOLS },
      { name: "assessment_date", label: "Assessment date", type: "date" },
      { name: "rationale", label: "Rationale for assessment", type: "rich" },
      { name: "selection_rationale", label: "Rationale for assessment selection", type: "rich" },
      { name: "tool_description", label: "Tool description and modules used", type: "rich" },
      { name: "client_score", label: "Describe the client score", type: "rich" },
    ],
    visual: [
      { name: "title", label: "Visual title" },
      { name: "analysis", label: "Visual analysis", type: "rich" },
    ],
  };
}

function visualHtml(visual, visualDefs) {
  const preview = visual.url.endsWith(".pdf")
    ? `<a class="file-link" href="${esc(visual.url)}" target="_blank" rel="noopener">Open PDF</a>`
    : `<img src="${esc(visual.url)}" alt="${esc(visual.title ?? "Uploaded visual")}">`;
  return `<div class="row visual" data-row-id="${visual.id}" data-kind="visual">
      <div class="visual-preview">${preview}</div>
      ${fieldsHtml(visualDefs, visual)}
      <button type="button" class="link danger" data-delete-visual="${visual.id}">Delete visual</button>
    </div>`;
}

function methodsHtml(methods, d) {
  if (!methods.length) return emptyHtml("No assessment method added yet.");
  return methods.map((m) => `
    <div class="row" data-row-id="${m.id}" data-kind="methods" data-method-id="${m.id}">
      ${fieldsHtml(d.method, m)}
      <div class="visuals">
        <h3>Visuals</h3>
        ${m.visuals.map((v) => visualHtml(v, d.visual)).join("")}
        <label class="upload"><input type="file" accept=".png,.jpg,.jpeg,.gif,.webp,.pdf" multiple data-upload="${m.id}">
          <span>Upload charts or images</span></label>
      </div>
      <button type="button" class="link danger" data-delete-row="${m.id}" data-kind-delete="methods">Delete method</button>
    </div>`).join("");
}

function readinessHtml(items, scores, levels) {
  const bySection = Object.keys(SECTION_LABELS).map((section) => `
    <div class="readiness-section">
      <div class="readiness-head"><h3>${SECTION_LABELS[section]}</h3><span class="score">Section score ${scores[section]}</span></div>
      ${items.filter((i) => i.section === section).map((i) => `
        <div class="readiness-item">
          <span class="readiness-label">${esc(i.label)}</span>
          <div class="segmented field" data-wrap="readiness_${i.item}" role="radiogroup" aria-label="${esc(i.label)}">
            <div class="segments">${levels.map((level) => `
              <label><input type="radio" name="r_${i.item}" value="${esc(level)}" data-readiness="${i.item}" ${i.readiness === level ? "checked" : ""}><span>${esc(level)}</span></label>`).join("")}
            </div><small class="err"></small>
          </div>
          <label class="field" data-wrap="notes_${i.item}"><span class="sr-only">Notes</span>
            <input type="text" placeholder="Notes" value="${esc(i.notes)}" data-readiness-notes="${i.item}"><small class="err"></small></label>
        </div>`).join("")}
    </div>`).join("");
  return `${bySection}<p class="overall-score">Overall score <strong>${scores.overall}</strong> of ${items.length * 2}</p>`;
}

export async function render(container, planId) {
  const o = await options();
  const d = defs(o);
  const base = `/${planId}/pages/assessment/`;
  const data = await api.get(base);
  const flag = (name, label) => `<label class="flag"><input type="checkbox" data-field="${name}" ${data[name] ? "checked" : ""}> ${label}</label>`;

  container.innerHTML = `
    <ul class="page-errors" hidden></ul>
    ${card("Assessment info", fieldsHtml(d.info, data), "Dates, records reviewed and what the parents told you.")}
    ${card("Maladaptive behaviors", `
      <div class="field" data-wrap="no_maladaptive_behavior">${flag("no_maladaptive_behavior", "No maladaptive behavior")}<small class="err"></small></div>
      ${data.no_maladaptive_behavior ? "" : `<div data-kind="behaviors">${rowListHtml(data.behaviors, d.behavior, "behavior")}${addRowButton("behavior")}</div>`}`,
      "Each behavior links to a DSM-5 symptom. Crisis plans and behavior goals build on these.")}
    ${card("Assessment summary", `
      ${fieldsHtml([{ name: "assessment_results", label: "Assessment results in terms of domains of deficit vs strengths", type: "rich" }], data)}
      <div class="derived"><span>Patient symptoms noted from DSM5 in assessment</span>
        ${data.dsm5_symptoms.length ? `<ul>${data.dsm5_symptoms.map((s) => `<li>${esc(s)}</li>`).join("")}</ul>` : '<p class="muted">Symptoms appear here once behaviors list them.</p>'}</div>
      ${fieldsHtml([{ name: "priorities", label: "Priorities/ goals based on assessment results", type: "rich" }], data)}`,
      "Narratives need at least 60 characters.")}
    ${card("Assessment methods", `
      <div class="field" data-wrap="methods"><small class="err"></small></div>
      <div data-kind-list="methods">${methodsHtml(data.methods, d)}<button type="button" data-add-method>Add method</button></div>`,
      "At least one tool, with a written rationale and the client's score.")}
    ${card("Barriers", fieldsHtml([{ name: "barriers", label: "Barriers to treatment", type: "multi", options: o.BARRIERS }], data), "Optional. Pick any that apply.")}
    ${card("Observations", fieldsHtml([{ name: "observations", label: "Observations noted during assessment", type: "rich" }], data))}
    ${card("Telehealth readiness", `
      <div class="field" data-wrap="telehealth_readiness_assessment_needed">${flag("telehealth_readiness_assessment_needed", "Telehealth readiness assessment needed")}<small class="err"></small></div>
      ${data.telehealth_readiness_assessment_needed ? `
        ${fieldsHtml([{ name: "telehealth_assessment_date", label: "Assessment date", type: "date" }], data)}
        ${readinessHtml(data.readiness_items, data.readiness_scores, o.READINESS_LEVELS)}` : ""}`,
      "Rate every item and add notes when telehealth is planned.")}`;

  const refresh = () => rerender(container, render, planId);

  bindAutosave(container, async ({ name, value, rowId, el }) => {
    const visual = el.closest('[data-kind="visual"]');
    if (visual) return api.patch(`${base}methods/${visual.closest("[data-method-id]").dataset.methodId}/visuals/${rowId}/`, { [name]: value });
    const kind = el.closest("[data-kind]")?.dataset.kind;
    if (rowId && kind) return api.patch(`${base}${kind}/${rowId}/`, { [name]: value });
    if (name === "no_maladaptive_behavior" && value && data.behaviors.length) {
      if (!confirm("Checking this deletes every behavior on this page. Continue?")) {
        el.checked = false;
        return;
      }
      for (const b of data.behaviors) await api.del(`${base}behaviors/${b.id}/`);
    }
    await api.patch(base, { [name]: value });
    if (name === "no_maladaptive_behavior" || name === "telehealth_readiness_assessment_needed") await refresh();
  });

  const behaviors = container.querySelector('[data-kind="behaviors"]');
  if (behaviors) {
    bindRowActions(behaviors, {
      noun: "behavior",
      add: () => api.post(`${base}behaviors/`, {}),
      remove: (id) => api.del(`${base}behaviors/${id}/`),
      refresh,
    });
  }

  container.addEventListener("click", async (event) => {
    const t = event.target;
    if (t.matches("[data-add-method]")) {
      await api.post(`${base}methods/`, {});
    } else if (t.dataset.kindDelete === "methods") {
      if (!confirm("Delete this method and its visuals?")) return;
      await api.del(`${base}methods/${t.dataset.deleteRow}/`);
    } else if (t.dataset.deleteVisual) {
      if (!confirm("Delete this visual?")) return;
      await api.del(`${base}methods/${t.closest("[data-method-id]").dataset.methodId}/visuals/${t.dataset.deleteVisual}/`);
    } else {
      return;
    }
    await refresh();
  });

  container.addEventListener("change", async (event) => {
    const t = event.target;
    if (t.dataset.upload) {
      const form = new FormData();
      for (const file of t.files) form.append("files", file);
      dispatchEvent(new Event("tp:saving"));
      const response = await fetch(`/api/v2/treatment_plans${base}methods/${t.dataset.upload}/visuals/`, { method: "POST", body: form });
      if (!response.ok) throw Object.assign(new Error("Upload failed"), { status: response.status, data: await response.json() });
      await refresh();
    } else if (t.dataset.readiness) {
      dispatchEvent(new Event("tp:saving"));
      await api.patch(`${base}readiness/${t.dataset.readiness}/`, { readiness: t.value });
      await refresh();
    } else if (t.dataset.readinessNotes) {
      dispatchEvent(new Event("tp:saving"));
      try {
        await api.patch(`${base}readiness/${t.dataset.readinessNotes}/`, { notes: t.value });
      } catch (err) {
        if (err.status !== 422) throw err;
        const wrap = t.closest("[data-wrap]");
        wrap.classList.add("invalid");
        wrap.dataset.errorKind = "save";
        wrap.querySelector(".err").textContent = "Notes need at least 8 characters";
        dispatchEvent(new Event("tp:invalid"));
        return;
      }
      dispatchEvent(new Event("tp:saved"));
    }
  });
}
