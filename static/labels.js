/** Display names for plan pages and access keys. */

export const LABELS = {
  information: "Information", medical: "Medical", referral: "Referral",
  medication: "Medication", therapy: "Therapy", education: "Education",
  family: "Family", child: "Child", assessment: "Assessment", crisis: "Crisis",
  goals: "Goals", discharge: "Discharge", treatment: "Treatment",
};

export const ADMIN_LABELS = { admin_roles: "Roles", admin_users: "Users", admin_goal_names: "Goal names", admin_clients: "Clients", admin_providers: "Providers", admin_assignments: "Client assignment", admin_history: "Change history" };

export const KEY_LABELS = {
  ...LABELS,
  create_plan: "Create plan",
  sign_plan: "Sign plan",
  all_clients: "All clients (read)",
  admin_roles: "Admin: Roles",
  admin_users: "Admin: Users",
  admin_goal_names: "Admin: Goal names",
  admin_clients: "Admin: Clients",
  admin_providers: "Admin: Providers",
  admin_assignments: "Admin: Client assignment",
  admin_history: "Admin: Change history",
};
