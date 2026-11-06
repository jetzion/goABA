/** Medical page: history, ASD diagnosis, additional diagnosis rows, selection groups, birth and development. */

import { api } from "../api.js";
import { addRowButton, bindAutosave, bindChips, bindRowActions, chipGroupHtml, fieldsHtml, options, rowListHtml } from "../form.js";
import { card, rerender } from "../ui.js";

const GROUPS = [
  ["EARLY_INTERVENTION", "Early Childhood Intervention (ECI)"],
  ["PREGNANCY_ISSUE", "Issues during pregnancy or birth"],
  ["REGRESSION", "Any regression in the areas of"],
];

function sections(o) {
  const num = (name, label) => ({ name, label, type: "number" });
  return {
    history: [
      { name: "allergies", label: "Allergies" },
      { name: "special_diets", label: "Special diets" },
      { name: "hearing_difficulty", label: "Hearing difficulties", type: "select", options: o.HEARING },
      { name: "hearing_screening_date", label: "Hearing screening date", type: "date" },
      { name: "vision_difficulty", label: "Vision difficulties", type: "select", options: o.VISION },
      { name: "vision_screening_date", label: "Vision screening date", type: "date" },
      { name: "trauma_history", label: "Trauma history", type: "rich" },
      { name: "hospitalization_history", label: "Surgical or hospitalization history", type: "rich" },
    ],
    asd: [
      { name: "asd_severity_level", label: "Severity level", type: "select", options: o.ASD_SEVERITY },
      { name: "asd_diagnosis_provider_name", label: "Provider name" },
      { name: "asd_diagnosis_city", label: "City" },
      { name: "asd_diagnosis_state", label: "State", type: "select", options: o.US_STATES },
      num("asd_diagnosis_year", "Year"),
    ],
    diagnosis: [
      { name: "diagnosis_name", label: "Additional diagnosis", type: "select", options: o.DIAGNOSES },
      { name: "provider_name", label: "Provider name" },
      { name: "city", label: "City" },
      { name: "state", label: "State", type: "select", options: o.US_STATES },
      num("year", "Year"),
    ],
    birth: [
      { name: "child_delivery_type", label: "Child delivery type", type: "select", options: o.DELIVERY_TYPES },
      num("child_gestational_age_weeks", "Weeks"),
      num("child_weight_at_birth_pounds", "Pounds"),
      num("child_weight_at_birth_ounces", "Ounces"),
      num("child_sitting_up_age_months", "Sitting up, months"),
      num("child_crawling_age_months", "Crawling, months"),
      num("child_walking_age_years", "Walking, years"),
      num("child_walking_age_months", "Walking, months"),
      num("child_standing_age_years", "Standing, years"),
      num("child_standing_age_months", "Standing, months"),
      num("child_babbling_age_months", "Babbling, months"),
      { name: "child_first_word", label: "First word" },
      { name: "child_second_word", label: "Second word" },
      num("child_first_words_age_months", "First words, months"),
    ],
  };
}

export async function render(container, planId) {
  const o = await options();
  const defs = sections(o);
  const data = await api.get(`/${planId}/pages/medical/`);
  const info = data.medical_info ?? {};

  container.innerHTML = `
    <ul class="page-errors" hidden></ul>
    ${card("Medical history", fieldsHtml(defs.history, info), "Allergies, diets, screenings and history.")}
    ${card("ASD diagnosis", fieldsHtml(defs.asd, info))}
    ${card("Additional diagnoses", rowListHtml(data.diagnoses, defs.diagnosis, "diagnosis") + addRowButton("diagnosis"), "Optional. Each diagnosis you add needs every field.")}
    ${card("Developmental history", GROUPS.map(([type, label]) => chipGroupHtml(type, label, o.MEDICAL_SELECTIONS[type], data.selections.filter((s) => s.selection_type === type))).join(""), "Pick at least one in each group. None cannot be combined with other choices.")}
    ${card("Birth and development", fieldsHtml(defs.birth, info), "Ages in months unless the label says years.")}`;

  const base = `/${planId}/pages/medical/`;
  bindAutosave(container, ({ name, value, rowId }) =>
    rowId ? api.patch(`${base}diagnoses/${rowId}/`, { [name]: value }) : api.patch(base, { [name]: value }));

  bindRowActions(container, {
    noun: "diagnosis",
    add: () => api.post(`${base}diagnoses/`, {}),
    remove: (id) => api.del(`${base}diagnoses/${id}/`),
    refresh: () => rerender(container, render, planId),
  });

  bindChips(container, {
    add: (type, value) => api.post(`${base}selections/`, { selection_type: type, value }),
    remove: (type, id) => api.del(`${base}selections/${type}/${id}/`),
  });
}
