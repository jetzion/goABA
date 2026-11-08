/** App shell: route #/plan/{id}/{page}, progress spine, page header, save state, failure banner. */

import { api, session } from "./api.js";
import { showPageErrors } from "./form.js";
import { icon } from "./icons.js";
import { ADMIN_LABELS, LABELS } from "./labels.js";
import { esc } from "./ui.js";

const LOCK_ICON = `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>`;

const DESCRIPTIONS = {
  information: "Client details, insurance and care team, from the client record.",
  medical: "Health history, the ASD diagnosis, other diagnoses and early development.",
  referral: "Who referred the client for ABA and which diagnostic tool they used.",
  medication: "Medications the client takes now.",
  therapy: "Therapy the client received before this plan.",
  education: "School setting, supports, and how the child feels about school.",
  family: "Parents, caregivers, siblings, family history and cultural considerations.",
  child: "How the child communicates, strengths and interests, behaviors and weekly availability.",
  assessment: "Assessment dates, maladaptive behaviors, methods, results and telehealth readiness.",
  crisis: "Crisis plans for maladaptive behaviors that can escalate.",
  goals: "Parent caregiver, skill acquisition and behavior reduction goals, with their targets.",
  discharge: "How and when services step down or end.",
  treatment: "Recommended services, hours and start date.",
};
const ADMIN_DESCRIPTIONS = {
  roles: "Define roles and what each role can view or edit across the app.",
  users: "People who can sign in, their role, and the provider they are.",
  goal_names: "The goal names offered when adding PCG, SAG and BRG goals.",
  clients: "Client records shown on each plan's Information page.",
  providers: "Clinicians who own plans and are assigned to clients.",
  assignments: "Which providers care for each client, and in what role.",
  history: "Who changed what, and when.",
};
const STATUS_TEXT ={ empty: "Not started", error: "Needs attention", completed: "Complete" };

let builtFor = null;
let plan = null;
let lastPlanId = "1";

/** #/plan/{id}/{page} or #/admin/{page}. Admin routes keep the last plan in the sidebar. */
function parseRoute() {
  if (/^(#\/?)?$|^#\/plans\/?$/.test(location.hash)) return { plansPage: true };
  if (location.hash === "#/password") return { passwordPage: true };
  if (location.hash === "#/mfa") return { mfaPage: true };
  const [, adminPage] = location.hash.match(/^#\/admin\/(\w+)/) || [];
  if (adminPage) return { adminPage };
  const [, planId, page] = location.hash.match(/^#\/plan\/(\d+)\/?(\w+)?/) || [];
  lastPlanId = planId || lastPlanId;
  return { planId: lastPlanId, page: page || visiblePages()[0] || "information" };
}

/** Plan pages the signed-in role can at least view, in nav order. */
function visiblePages() {
  return Object.keys(LABELS).filter((page) => (access[page] ?? "none") !== "none");
}

/** Read-only when the plan is signed, the user cannot edit this plan (client rules), or the role can only view the page. */
function isReadOnly(page) {
  return plan.status === "signed" || !plan.can_edit || (page !== "information" && access[page] !== "edit");
}

function ring() {
  return `<svg class="ring" viewBox="0 0 24 24" aria-hidden="true">
    <circle class="ring-track" cx="12" cy="12" r="9"/>
    <circle class="ring-fill" cx="12" cy="12" r="9" pathLength="100"/>
    <path class="ring-check" d="M8 12.4l2.7 2.6L16 9.6" pathLength="1"/>
    <path class="ring-alert" d="M12 7.5v5.2M12 16.2v.1" pathLength="1"/>
  </svg>`;
}

async function buildShell(planId) {
  const nav = document.getElementById("nav");
  nav.innerHTML = `<span class="nav-indicator" aria-hidden="true"></span><ol>${visiblePages().map((page, i) => `
    <li style="--i:${i}"><a href="#/plan/${planId}/${page}" data-page="${page}" data-status="empty">
      ${ring()}<span class="nav-label">${LABELS[page]}</span><span class="sr-only"></span></a></li>`).join("")}</ol>`;
  plan = await api.get(`/${planId}/`);
  const client = visiblePages().includes("information") ? (await api.get(`/${planId}/pages/information/`)).client : null;
  document.querySelector(".client-name").textContent = client ? `${client.first_name} ${client.last_name}` : `Client ${plan.client_id}`;
  document.querySelector(".client-meta").textContent = `Plan ${plan.id}, bay ${plan.bay}`;
  builtFor = planId;
}

async function refreshNav() {
  const { planId, page } = parseRoute();
  const statuses = await api.get(`/${planId}/pages/`);
  for (const s of statuses) {
    const link = document.querySelector(`#nav [data-page="${s.page}"]`);
    if (!link) continue;
    if (link.dataset.status !== "completed" && s.status === "completed" && link.dataset.seen) replay(link, "just-completed");
    link.dataset.seen = "1";
    link.dataset.status = s.status;
    link.querySelector(".sr-only").textContent = `, ${STATUS_TEXT[s.status]}`;
    link.toggleAttribute("aria-current", s.page === page);
  }
  const done = statuses.filter((s) => s.status === "completed").length;
  const count = document.querySelector("#progress strong");
  if (Number(count.textContent) < done) replay(document.querySelector(".progress-bar"), "grew");
  count.textContent = done;
  document.querySelector(".progress-bar").style.transform = `scaleX(${done / statuses.length})`;
  moveIndicator();
  renderSignBox(done === statuses.length);
  const current = statuses.find((s) => s.page === page);
  const pill = document.getElementById("page-status");
  pill.hidden = !current;
  if (!current) return null;
  if (pill.dataset.status && pill.dataset.status !== current.status) replay(pill, "changed");
  pill.dataset.status = current.status;
  pill.textContent = STATUS_TEXT[current.status];
  return current;
}

/** Restart a one-shot CSS animation by re-adding its class. */
function replay(el, className) {
  el.classList.remove(className);
  void el.offsetWidth;
  el.classList.add(className);
}

/** Slide the nav highlight to the current page. */
function moveIndicator() {
  const active = document.querySelector("#nav [aria-current]");
  const indicator = document.querySelector(".nav-indicator");
  if (indicator) indicator.style.opacity = active ? "" : "0";
  if (!active || !indicator) return;
  const li = active.parentElement;
  indicator.style.setProperty("--y", `${li.offsetTop}px`);
  indicator.style.setProperty("--h", `${li.offsetHeight}px`);
}

/** Sidebar signing: a disabled button until every page is complete, then the signer once signed. */
function renderSignBox(allComplete) {
  const box = document.getElementById("sign-box");
  if (plan.status === "signed") {
    box.innerHTML = `<div class="signed-by">${LOCK_ICON}<div><strong>Signed</strong><span>${esc(plan.signature)}</span></div></div>`;
    return;
  }
  if (access.sign_plan !== "edit" || !plan.can_edit) {
    box.innerHTML = "";
    return;
  }
  box.innerHTML = `<button type="button" class="sign-button" id="sign-open" ${allComplete ? "" : "disabled"}>${LOCK_ICON}Sign plan</button>
    <p class="sign-hint">${allComplete ? "Every page is complete. Signing locks the plan." : "Complete all 13 pages to sign."}</p>`;
}

/** A read-only page disables every control except navigation and tabs. */
function applyReadOnly(root) {
  const readOnly = isReadOnly(parseRoute().page);
  document.body.classList.toggle("is-readonly", readOnly);
  if (!readOnly) return;
  root.querySelectorAll("input, select, textarea, button:not(.tab)").forEach((el) => { el.disabled = true; });
  root.querySelectorAll("[contenteditable]").forEach((el) => el.setAttribute("contenteditable", "false"));
}

async function refreshStatus() {
  if (!parseRoute().page) return;
  const status = await refreshNav();
  if (!status) return;
  const page = document.getElementById("page");
  showPageErrors(page, status);
  applyReadOnly(page);
}

/** The role can view no plan page: say so instead of showing an empty page. */
/** A plan link the user cannot open: missing (404) or a client they have no access to (403). */
function renderNoPlan(status) {
  enterNonPlanPage("", "Plan not available", "plans", {});
  const message = status === 404
    ? "This plan does not exist."
    : "You do not have access to this plan's client. An admin can assign you to the client.";
  document.getElementById("page").innerHTML = `<p class="empty-note">${message} <a href="#/plans">Back to plans</a></p>`;
}

function renderNoPages() {
  document.getElementById("page-title").textContent = "No plan pages";
  document.title = "goABA";
  document.getElementById("page-icon").innerHTML = icon("admin");
  document.getElementById("page-status").hidden = true;
  document.getElementById("progress").hidden = true;
  document.getElementById("page").innerHTML = `<p class="empty-note">Your role cannot view any treatment plan page. Ask an admin to give your role access.</p>`;
}

/** Admin pages: a header, a one-line intro and the page module. The sidebar keeps the last plan. */
/** Pages outside a plan (Plans, Admin): no plan in the sidebar, no status pill, nothing read-only. */
function enterNonPlanPage(prefix, label, iconName, current) {
  document.body.classList.add("no-plan");
  document.body.classList.remove("is-readonly");
  scrollTo({ top: 0 });
  const title = document.getElementById("page-title");
  title.innerHTML = `${prefix ? `<span class="title-prefix">${esc(prefix)} - </span>` : ""}${esc(label)}`;
  document.title = prefix ? `${prefix} - ${label}` : label;
  replay(title, "enter");
  const pageIcon = document.getElementById("page-icon");
  pageIcon.hidden = false;
  pageIcon.innerHTML = icon(iconName);
  replay(pageIcon, "enter");
  document.getElementById("page-status").hidden = true;
  document.getElementById("save-state").textContent = "";
  markAdminNav(current.admin ?? null);
  markPlansNav(!!current.plans);
}

function markPlansNav(on) {
  document.querySelector("#plans-link").toggleAttribute("aria-current", on);
}

/** The Plans page: every plan by client, and the New plan form. */
async function renderPlans() {
  enterNonPlanPage("", "Plans", "plans", { plans: true });
  const intro = document.createElement("div");
  intro.className = "page-intro";
  intro.innerHTML = `<p>Open a treatment plan, or start a new one for a client.</p>`;
  const root = document.createElement("div");
  root.className = "page-body";
  document.getElementById("page").replaceChildren(intro, root);
  const module = await import("./plans.js");
  await module.render(root, { canCreate: access.create_plan === "edit", isProvider: currentUser.provider_id !== null });
}

async function renderAdmin(adminPage) {
  if ((access[`admin_${adminPage}`] ?? "none") === "none") {
    location.replace("#/plans");
    return;
  }
  const label = ADMIN_LABELS[`admin_${adminPage}`];
  enterNonPlanPage("Admin", label, "admin", { admin: adminPage });
  const intro = document.createElement("div");
  intro.className = "page-intro";
  intro.innerHTML = `<span class="page-step">Admin</span><p>${ADMIN_DESCRIPTIONS[adminPage]}</p>`;
  const root = document.createElement("div");
  root.className = "page-body";
  document.getElementById("page").replaceChildren(intro, root);
  const module = await import(`./admin/${adminPage}.js`);
  await module.render(root, { canEdit: access[`admin_${adminPage}`] === "edit", me: currentUser.id });
}

async function render() {
  const { planId, page, adminPage, plansPage, passwordPage, mfaPage } = parseRoute();
  if (plansPage) return renderPlans();
  if (passwordPage) return renderChangePassword(false);
  if (mfaPage) return renderMfaPage();
  if (adminPage) return renderAdmin(adminPage);
  markAdminNav(null);
  markPlansNav(false);
  document.body.classList.remove("no-plan");
  document.getElementById("progress").hidden = false;
  if (builtFor !== planId) {
    try {
      await buildShell(planId);
    } catch (err) {
      if (![403, 404].includes(err.status)) throw err;
      return renderNoPlan(err.status);
    }
  }
  const pages = visiblePages();
  if (!pages.length) return renderNoPages();
  if (!pages.includes(page)) {
    location.replace(`#/plan/${planId}/${pages[0]}`);
    return;
  }
  scrollTo({ top: 0 });
  const title = document.getElementById("page-title");
  title.innerHTML = `<span class="title-prefix">Treatment Plan - </span>${LABELS[page]}`;
  document.title = `Treatment Plan - ${LABELS[page]}`;
  replay(title, "enter");
  const pageIcon = document.getElementById("page-icon");
  pageIcon.innerHTML = icon(page);
  replay(pageIcon, "enter");
  document.getElementById("page-status").dataset.status = "";
  document.getElementById("save-state").textContent = "";
  const container = document.getElementById("page");
  const module = await import(`./pages/${page}.js`).catch(() => null);
  const index = pages.indexOf(page);
  const intro = document.createElement("div");
  intro.className = "page-intro";
  intro.innerHTML = `<span class="page-step">Page ${index + 1} of ${pages.length}</span><p>${DESCRIPTIONS[page]}</p>`
    + (plan.status === "signed" ? `<p class="signed-banner">${LOCK_ICON}Signed by ${esc(plan.signature)}. This plan is read-only.</p>`
      : !plan.can_edit ? `<p class="signed-banner view-banner">${icon("information", 16)}You can view this plan but not change it: you are not assigned to this client.</p>`
      : isReadOnly(page) ? `<p class="signed-banner view-banner">${icon("information", 16)}Your role can view this page but not change it.</p>` : "");
  const root = document.createElement("div");
  root.className = "page-body";
  const pager = document.createElement("nav");
  pager.className = "pager";
  pager.setAttribute("aria-label", "Previous and next page");
  const link = (i, dir) => {
    if (i < 0 || i >= pages.length) return "<span></span>";
    const label = `${dir === "prev" ? "Previous" : "Next"}: ${LABELS[pages[i]]}`;
    const arrow = icon(dir, 18);
    return `<a class="pager-btn pager-${dir}" href="#/plan/${planId}/${pages[i]}">${dir === "prev" ? arrow : ""}<span>${label}</span>${dir === "next" ? arrow : ""}</a>`;
  };
  pager.innerHTML = link(index - 1, "prev") + link(index + 1, "next");
  container.replaceChildren(intro, root, pager);
  if (!module) {
    root.innerHTML = `<p class="empty-note">This page is not built yet.</p>`;
    await refreshNav();
    return;
  }
  await module.render(root, planId);
  await refreshStatus();
  document.querySelector("#nav [aria-current]")?.scrollIntoView({ block: "nearest", inline: "nearest" });
}

function setSaveState(text, state) {
  const el = document.getElementById("save-state");
  el.textContent = text;
  el.dataset.state = state;
}

function showFailure(event) {
  const reason = event.reason ?? event.error;
  const detail = reason?.data?.detail;
  const banner = document.getElementById("failure");
  banner.textContent = `The change was not saved: ${typeof detail === "string" ? detail : reason?.message ?? reason}`;
  banner.hidden = false;
  setSaveState("Not saved", "failed");
}

const signDialog = document.getElementById("sign-dialog");
const signForm = document.getElementById("sign-form");

document.getElementById("sign-box").addEventListener("click", (event) => {
  if (!event.target.closest("#sign-open")) return;
  signForm.reset();
  document.getElementById("sign-error").textContent = "";
  signDialog.showModal();
});
document.getElementById("sign-cancel").addEventListener("click", () => signDialog.close());
signForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const { planId } = parseRoute();
  try {
    plan = { ...plan, ...(await api.post(`/${planId}/sign/`, { signature: signForm.signature.value })) };
  } catch (err) {
    if (!err.status) throw err;
    const detail = err.data?.detail;
    document.getElementById("sign-error").textContent = typeof detail === "string" ? detail : "Enter your full name.";
    return;
  }
  signDialog.close();
  await render();
});

addEventListener("unhandledrejection", showFailure);
addEventListener("error", showFailure);
addEventListener("tp:saving", () => setSaveState("Saving", "saving"));
addEventListener("tp:saved", () => { setSaveState("All changes saved", "saved"); refreshStatus(); });
addEventListener("tp:invalid", () => setSaveState("Fix the highlighted field", "failed"));
addEventListener("hashchange", () => {
  if (!fullySignedIn()) return;
  document.getElementById("failure").hidden = true;
  render();
});

let currentUser = null;
let access = {};

/** Past every sign-in step, so the hash routes to pages. */
function fullySignedIn() {
  return currentUser && !currentUser.must_change_password && !currentUser.mfa_pending && !currentUser.mfa_setup_required;
}

/** Sidebar Admin section: one link per admin page the user can at least view. */
function renderAdminNav() {
  const nav = document.getElementById("admin-nav");
  const pages = Object.keys(ADMIN_LABELS).filter((key) => (access[key] ?? "none") !== "none");
  nav.hidden = !pages.length;
  nav.innerHTML = `<h2 class="admin-nav-title">Admin</h2><ol>${pages.map((key) => {
    const page = key.replace("admin_", "");
    return `<li><a href="#/admin/${page}" data-admin="${page}">${icon("admin", 18)}<span>${ADMIN_LABELS[key]}</span></a></li>`;
  }).join("")}</ol>`;
}

function markAdminNav(adminPage) {
  document.querySelectorAll("#admin-nav [data-admin]").forEach((a) => a.toggleAttribute("aria-current", a.dataset.admin === adminPage));
}

/** Sidebar box: who is signed in, with Change password, Authenticator codes and Sign out. */
function renderUserBox(user) {
  const box = document.getElementById("user-box");
  box.innerHTML = `<div class="user-who"><span>Signed in as</span><strong>${esc(user.display_name)}</strong><small>${esc(user.role)}</small></div>
    <div class="user-actions"><a href="#/password">Change password</a><a href="#/mfa">Authenticator codes</a><button type="button" class="link" id="sign-out">Sign out</button></div>`;
  box.hidden = false;
}

/** Sign-in and forced password change show only their form. */
function renderBare(title) {
  document.body.classList.add("no-plan");
  for (const id of ["progress", "page-icon", "plans-link", "page-status", "user-box"]) document.getElementById(id).hidden = true;
  document.getElementById("page-title").textContent = title;
  document.title = `goABA - ${title}`;
}

function formError(form, err) {
  const detail = err.data?.detail;
  form.querySelector(".err").textContent = typeof detail === "string" ? detail : "Check the highlighted fields.";
}

function renderSignIn() {
  renderBare("Sign in");
  document.getElementById("page").innerHTML = `<section class="section">
    <header class="section-head"><h2>Sign in</h2><p>Use the email and password your admin gave you.</p></header>
    <form class="section-body auth-form" id="sign-in-form">
      <label class="field"><span>Email</span><input type="email" name="email" autocomplete="username" required autofocus></label>
      <label class="field"><span>Password</span><input type="password" name="password" autocomplete="current-password" required></label>
      <p class="err" role="alert"></p>
      <button type="submit">Sign in</button>
    </form>
  </section>`;
  const form = document.getElementById("sign-in-form");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await session.signIn(form.email.value, form.password.value);
    } catch (err) {
      if (!err.status) throw err;
      formError(form, err);
      form.password.value = "";
      return;
    }
    location.reload();
  });
}

/** Second sign-in step: the 6-digit code from the authenticator app. */
function renderCodeStep() {
  renderBare("Authenticator code");
  document.getElementById("page").innerHTML = `<section class="section">
    <header class="section-head"><h2>Authenticator code</h2><p>Enter the 6-digit code from your authenticator app.</p></header>
    <form class="section-body auth-form" id="code-form">
      <label class="field"><span>Code</span><input name="code" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9 ]{6,7}" maxlength="7" required autofocus></label>
      <p class="err" role="alert"></p>
      <div class="actions"><button type="submit">Continue</button><button type="button" class="link" id="sign-out">Sign out</button></div>
    </form>
  </section>`;
  const form = document.getElementById("code-form");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await session.enterCode(form.code.value);
    } catch (err) {
      if (!err.status) throw err;
      if (!(await session.get()).user) return location.reload();
      formError(form, err);
      form.code.value = "";
      return;
    }
    location.reload();
  });
}

/** Set up authenticator codes: scan the QR code, then confirm with the first code. Forced for Admin users. */
async function renderMfaSetup(forced) {
  if (forced) renderBare("Set up authenticator codes");
  else enterNonPlanPage("", "Authenticator codes", "admin", {});
  const setup = await session.startMfaSetup();
  const hint = forced ? "Admin users sign in with a code from an authenticator app as well as a password." : "You will enter a code from the app each time you sign in.";
  document.getElementById("page").innerHTML = `<section class="section">
    <header class="section-head"><h2>Set up authenticator codes</h2><p>${hint}</p></header>
    <form class="section-body auth-form" id="mfa-setup-form">
      <p class="mfa-step">1. In an authenticator app (such as Google Authenticator, Microsoft Authenticator or 1Password), add an account by scanning this code.</p>
      <div class="mfa-qr">${setup.qr_svg}</div>
      <p class="mfa-step">Cannot scan? Enter this key instead: <code class="mfa-key">${esc(setup.secret.match(/.{1,4}/g).join(" "))}</code></p>
      <label class="field"><span>2. Enter the 6-digit code the app shows</span><input name="code" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9 ]{6,7}" maxlength="7" required></label>
      <p class="err" role="alert"></p>
      <div class="actions"><button type="submit">Turn on</button>${forced ? `<button type="button" class="link" id="sign-out">Sign out</button>` : ""}</div>
    </form>
  </section>`;
  const form = document.getElementById("mfa-setup-form");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      currentUser = await session.enableMfa(form.code.value);
    } catch (err) {
      if (!err.status) throw err;
      formError(form, err);
      form.code.value = "";
      return;
    }
    if (!forced) return renderMfaPage();
    location.replace("#/plans");
    location.reload();
  });
}

/** Your authenticator codes: on or off. Admin users must keep them on; others turn them off with a current code. */
function renderMfaPage() {
  enterNonPlanPage("", "Authenticator codes", "admin", {});
  const on = currentUser.mfa_enabled;
  const body = !on
    ? `<p class="mfa-step">Off. Turn them on to enter a code from an authenticator app each time you sign in, as well as your password.</p>
      <div class="actions"><button type="button" id="mfa-start">Set up</button></div>`
    : currentUser.mfa_required
      ? `<p class="mfa-step">On. Admin users must keep authenticator codes on. If you lose your phone, another Admin can reset them on Admin - Users.</p>`
      : `<p class="mfa-step">On. You enter a code from your authenticator app each time you sign in.</p>
      <label class="field"><span>To turn them off, enter a current code</span><input name="code" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9 ]{6,7}" maxlength="7" required></label>
      <p class="err" role="alert"></p>
      <div class="actions"><button type="submit">Turn off</button></div>`;
  document.getElementById("page").innerHTML = `<section class="section">
    <header class="section-head"><h2>Authenticator codes</h2><p>A second sign-in step that protects your account if your password leaks.</p></header>
    <form class="section-body auth-form" id="mfa-form">${body}</form>
  </section>`;
  document.getElementById("mfa-start")?.addEventListener("click", () => renderMfaSetup(false));
  const form = document.getElementById("mfa-form");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      currentUser = await session.disableMfa(form.code.value);
    } catch (err) {
      if (!err.status) throw err;
      formError(form, err);
      form.code.value = "";
      return;
    }
    renderMfaPage();
  });
}

/** Change your own password. Forced after a temporary password, otherwise reached from the sidebar. */
function renderChangePassword(forced) {
  if (forced) renderBare("Choose a new password");
  else enterNonPlanPage("", "Change password", "admin", {});
  const hint = forced ? "Your admin gave you a temporary password. Choose your own to continue." : "Other devices are signed out when you change it.";
  document.getElementById("page").innerHTML = `<section class="section">
    <header class="section-head"><h2>${forced ? "New password" : "Change password"}</h2><p>${hint}</p></header>
    <form class="section-body auth-form" id="password-form">
      <label class="field"><span>Current password</span><input type="password" name="current" autocomplete="current-password" required></label>
      <label class="field"><span>New password (8 or more characters)</span><input type="password" name="next" autocomplete="new-password" minlength="8" required></label>
      <label class="field"><span>Repeat new password</span><input type="password" name="repeat" autocomplete="new-password" minlength="8" required></label>
      <p class="err" role="alert"></p>
      <div class="actions"><button type="submit">Change password</button>${forced ? `<button type="button" class="link" id="sign-out">Sign out</button>` : ""}</div>
    </form>
  </section>`;
  const form = document.getElementById("password-form");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (form.next.value !== form.repeat.value) {
      form.querySelector(".err").textContent = "The new passwords do not match.";
      return;
    }
    try {
      await session.changePassword(form.current.value, form.next.value);
    } catch (err) {
      if (!err.status) throw err;
      formError(form, err);
      return;
    }
    if (forced) {
      location.replace("#/plans");
      location.reload();
      return;
    }
    form.reset();
    form.querySelector(".err").textContent = "";
    document.getElementById("save-state").textContent = "Password changed";
    document.getElementById("save-state").dataset.state = "saved";
  });
}

document.addEventListener("click", async (event) => {
  if (!event.target.closest("#sign-out")) return;
  await session.signOut();
  location.replace(location.pathname);
});

async function start() {
  const info = await session.get();
  currentUser = info.user;
  access = info.access;
  if (!currentUser) return renderSignIn();
  if (currentUser.mfa_pending) return renderCodeStep();
  if (currentUser.must_change_password) return renderChangePassword(true);
  if (currentUser.mfa_setup_required) return renderMfaSetup(true);
  renderUserBox(currentUser);
  renderAdminNav();
  render();
}

start();
