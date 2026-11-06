/** Family page: members, siblings, family history lists and cultural considerations. */

import { api } from "../api.js";
import { addRowButton, bindAutosave, bindChips, bindRowActions, chipGroupHtml, fieldsHtml, options, rowListHtml } from "../form.js";
import { card, rerender } from "../ui.js";

const NOT_CAREGIVER = "Parent not a caregiver";
const LISTS = [
  ["MATERNAL_MEDICAL_HISTORY", "Maternal medical history", "maternal_medical_history"],
  ["PATERNAL_MEDICAL_HISTORY", "Paternal medical history", "paternal_medical_history"],
  ["COMMUNITY_SUPPORT", "Community support", "community_support"],
];

function memberDefs(o) {
  const all = [
    { name: "full_name", label: "First & last name" },
    { name: "member_role", label: "Role", type: "select", options: o.MEMBER_ROLES },
    { name: "caregiver_type", label: "Primary/secondary caregiver", type: "select", options: o.CAREGIVER_TYPES },
    { name: "relationship_to_client", label: "Relationship to child", type: "select", options: o.RELATIONSHIPS },
    { name: "custody_type", label: "Child custody", type: "select", options: o.CUSTODY_TYPES },
    { name: "marital_status", label: "Marital status", type: "select", options: o.MARITAL_STATUSES },
    { name: "job_title", label: "Job" },
    { name: "email", label: "Email", type: "email" },
    { name: "phone", label: "Phone", type: "tel" },
    { name: "street_address_line_one", label: "Street address line one" },
    { name: "street_address_line_two", label: "Address line two (Apartment/unit)" },
    { name: "street_address_city", label: "City" },
    { name: "street_address_state", label: "State", type: "select", options: [...o.US_STATES, "CZ"] },
    { name: "street_address_zip", label: "Zip code" },
  ];
  return (row) => (row.member_role === NOT_CAREGIVER ? all.filter((d) => d.name !== "caregiver_type") : all);
}

function siblingDefs(o) {
  return [
    { name: "sibling_relationship", label: "Sibling relation", type: "select", options: o.SIBLING_RELATIONSHIPS },
    { name: "sibling_age", label: "Age", type: "number" },
    { name: "sibling_diagnosis", label: "Diagnosis" },
  ];
}

/** A parent who is not a caregiver has no caregiver type, so changing to that role clears it. */
function memberPatch(name, value) {
  if (name === "member_role" && value === NOT_CAREGIVER) return { member_role: value, caregiver_type: null };
  return { [name]: value };
}

export async function render(container, planId) {
  const o = await options();
  const base = `/${planId}/pages/family/`;
  const data = await api.get(base);

  container.innerHTML = `
    <ul class="page-errors" hidden></ul>
    ${card("Family members", `
      <div class="field" data-wrap="members"><small class="err"></small></div>
      ${rowListHtml(data.members, memberDefs(o), "family member")}
      <div data-rows="members">${addRowButton("family member")}</div>`,
      "Parents and caregivers. Add at least one. Only one can be the primary caregiver.")}
    ${card("Siblings", `
      ${rowListHtml(data.siblings, siblingDefs(o), "sibling")}
      <div data-rows="siblings">${addRowButton("sibling")}</div>`,
      "Optional. Each sibling you add needs every field.")}
    ${card("Family history and support",
      LISTS.map(([type, label, key]) => chipGroupHtml(type, label, o.FAMILY_INFO_TYPES[type], data[key])).join(""),
      "Pick at least one in each list.")}
    ${card("Cultural considerations", fieldsHtml([{ name: "cultural_consideration", label: "Cultural considerations", type: "rich" }], data),
      "Language, beliefs and customs that shape how the family takes part in therapy.")}`;

  const refresh = () => rerender(container, render, planId);
  bindAutosave(container, async ({ name, value, rowId, el }) => {
    if (!rowId) return api.patch(base, { [name]: value });
    const kind = el.closest(".section").querySelector("[data-rows]").dataset.rows;
    await api.patch(`${base}${kind}/${rowId}/`, memberPatch(name, value));
    if (name === "member_role") await refresh();
  });
  bindChips(container, {
    add: (type, value) => api.post(`${base}additional_info/`, { info_type: type, value }),
    remove: (_type, id) => api.del(`${base}additional_info/${id}/`),
  });

  container.querySelectorAll("[data-rows]").forEach((section) => {
    const kind = section.dataset.rows;
    bindRowActions(section.closest(".section"), {
      noun: kind === "members" ? "family member" : "sibling",
      add: () => api.post(`${base}${kind}/`, {}),
      remove: (id) => api.del(`${base}${kind}/${id}/`),
      refresh,
    });
  });
}
