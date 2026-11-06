# Plan: Treatment Plan v3 web app

Build a working web app from `TREATMENT-PLAN.md`: a JSON API that follows the spec, and a browser UI for all 13 pages.

## Stack

- **Backend:** Python, FastAPI, Pydantic v2, SQLAlchemy 2. Managed with `uv`.
- **Database:** SQLite file. Array columns are JSON columns.
- **Frontend:** Plain HTML, CSS and ES-module JavaScript served by FastAPI. No build step.
- **Tests:** pytest with FastAPI `TestClient`, one test file per page.

## Scope decisions

- Steps 1 to 17: single local user acting as a BCBA, no login. Roles come in step 18 (Admin area). The feature flag and log redaction are left out.
- Seed data provides one client, assignments and insurance, so Information can render.
- Visual uploads are stored in a local `uploads/` folder.
- Goals gets a UI (PCG, SAG, BRG tabs), since the spec has the API but no form.
- Where the spec contradicts itself, follow the API rules and record the choice under "Decisions" below.

## Layout

```
app/
  main.py          FastAPI app, static files, router wiring
  db.py            engine, session, Base
  models/          one module per page (tables)
  routes/          one module per page: schemas, routes and completion check
  completion/      page status types, checker registry, shared helpers
  enums.py         all option lists (also served at GET /api/v2/options/)
  rules.py         shared value rules (phone, state, month, rich text)
static/
  index.html       shell: nav + page container
  app.js           router, nav status badges
  api.js           fetch helpers
  form.js          field rendering, autosave, inline save and completion errors
  ui.js            escaping, cards, re-render
  pages/*.js       one module per page
  style.css
tests/
```

## Design

- Palette: iris `#5B4CF0` for actions, sunrise `#FF8A3D` for focus and highlights (never text), green `#15803D` complete, red `#D93636` needs attention, cool paper `#F4F6FB`, navy ink `#172036`. Sidebar is deep navy `#161A33` with soft iris and sunrise glows.
- Type: Bricolage Grotesque for titles, Plus Jakarta Sans for everything else.
- Sidebar: gradient brand mark, client, progress card with an iris-to-green bar, and one status ring per page joined by a line.
- Backdrop: behind the page body, four large pastel blobs (lavender, sky, peach, mint) drift slowly and small glossy orbs bob in the right gutter and header band, never behind content; orbs hide below 1300px wide.
- Sections: title and hint above a full-width frosted-glass card (translucent white, backdrop blur, bright edge, tinted shadow) that lifts slightly on hover. The intro, flags, tabs, goal cards, page links and sticky header use the same glass. Fields and option chips are solid white with a `#C3CBDB` edge and a small shadow so they stand out on the glass; repeating rows get a faint cool tint for the same reason. Sticky page header with status pill and save indicator.
- Motion: nav items draw in on load; a highlight slides to the current page; a ring pops and glows when its page completes; the progress bar shimmers when it grows; the title and sections enter staggered on each page change; chips pop when picked; the save indicator draws a check; buttons lift on hover. All motion is off under reduced motion.
- Page header: a gradient icon tile for the page, the title "Treatment Plan - <Page>" (also the browser tab title) with "Treatment Plan -" in a lighter weight, the status pill, the save indicator, and a violet-to-sunrise rule that draws in under the header.
- Page footer: Previous (outlined) and Next (solid violet) pill buttons labeled with the neighboring page, chevrons nudge on hover; full-width on phones.
- Missing required values get a soft tinted border; values the API rejected get a red fill and a small nudge.
- Page body: a "Page N of 13" pill and one-line description under the header; filled inputs turn white with a focus ring; rich text has a bold, italic and list toolbar; repeating rows are numbered; empty lists show a dashed empty state; Field grids use subgrid so inputs line up when a label wraps. Free-text lists (Child strengths, weaknesses, interests, dislikes) show the add field first and the entries below as wrapping bubbles with a remove × (focus returns to the field after each add). Option groups (chips and multi-selects) are laid out in equal columns so choices line up vertically; long labels wrap inside their cell, and phones show one column.

## Steps

Each step ends with its check. Do not start the next step until the check passes.

### 0. Tooling (done)
- Install `uv` (`brew install uv`), `uv init`, add fastapi, uvicorn, sqlalchemy, pydantic, pytest, httpx, nh3 (HTML sanitizer).
- **Check:** `uv run python -c "import fastapi"` works.

### 1. Skeleton (done)
- `db.py`, `treatment_plan` and `client` tables, seed script.
- `POST /api/v2/treatment_plans/`, `GET /{id}/`, `GET /{id}/pages/` returning all 13 pages as `empty`.
- Static shell with left nav listing the 13 pages.
- **Check:** pytest creates a plan and gets 13 statuses. Browser shows the nav.

### 2. Shared rules (done)
- `enums.py`, `rules.py`: phone, email, state (+ `CZ` variant), first-of-month, `mm-yyyy` goal month, rich-text sanitize + visible-length.
- Base Pydantic model: `extra="forbid"`, strip spaces, blank to null.
- **Check:** unit tests for each rule.

### 3. Information page (read-only) (done)
- API + UI from seeded client, insurance, assignments.
- **Check:** API test + page renders in browser.

### 4–13. One page per step, in nav order (done)
All done.

Medical, Referral, Medication, Therapy, Education, Family, Child, Assessment, Crisis, Discharge, Treatment.

For each page:
1. Model + table.
2. Schemas with save rules.
3. Routes from the spec's API table.
4. Completion function returning `empty | completed | error` with errors, wired into `/pages/`.
5. Tests: one save-rule rejection, one valid save, each completion state.
6. UI form: field-at-a-time save on blur, inline errors, row add/delete, confirm dialogs where the spec asks.
- **Check:** tests pass, then drive the page in headless Chrome (DevTools protocol script) and confirm saves, inline errors and the nav badge.

### 14. Goals: PCG, SAG, BRG (done)
Built in three sub-steps (PCG, then SAG, then BRG), each with goal, target, stage history and its tests. Then a combined `goals` status.
- **Check:** tests for method fields, mastery direction, stage transitions; a goal completed in the browser.

### 15. Cross-page rules (done, built with each page)
- Child schedule needs School slot (Education) and Other therapies slot (Therapy).
- Medication/Therapy month dates after client date of birth.
- BRG DSM-5 symptom must exist on Assessment. Crisis behavior must belong to the plan.
- **Check:** tests that change one page and see the other page's status flip.

### 16. Signing and read-only (done)
- Sign action allowed only when every page is `completed` (Crisis may be complete via its checkbox).
- Signed plan: all writes return an error, UI goes read-only.
- **Check:** tests for blocked and allowed signing; UI shows disabled fields.

### 17. Clone and README (done)
- (done) Clone from an existing plan (copy all page rows, remap behavior ids for crisis plans).
- (done) Short README: install, seed, run, test.
- **Check:** cloned plan has the same page statuses as its source.

### 18. Admin area: Roles (done)
An Admin section in the sidebar holds app management. Its pages, in order: Roles, Users, Goal names, Clients, Client assignment. Roles comes first; the rest are later steps.

Rules:
- Access is a matrix: pages down the side, roles across the top. Each cell is one level: None, View or Edit (Edit includes View). Information offers only None or View.
- Rows: the 13 plan pages (Goals is one row), the actions Create plan and Sign plan (Allowed or Not allowed), and each Admin page.
- The page list lives in code (`PAGES` plus action and admin keys), not in a table. A key with no stored cell is None.
- Starting roles: only Admin, with full access to everything. Admin is locked: it cannot be deleted, renamed or have any cell lowered. Other roles are added by Admin.
- One role per user.
- A role that users still hold cannot be deleted (409, with the user count).
- The server enforces access on every route: GET needs View, other methods need Edit, missing access is 403. Hiding things in the UI is not the protection.
- The UI hides pages at None and shows View pages read-only, reusing the signed-plan read-only mode.

Sub-steps:
1. (done) Tables `role` (name, `locked`), `role_permission` (role, key, level) and `app_user` (name, role, optional provider). Keys and allowed levels in `app/access.py`. Seed the Admin role and make provider 1 an Admin user.
   - **Check:** tests for the seed, Admin's levels, stored cells and the none default. The Admin lock is tested with the Roles API in sub-step 4.
2. (done) Current user: a "sign in as" user picker stored in a cookie, for building and testing only (real login is step 22). One dependency gives every route the current user, replacing the fixed provider 1.
   - **Check:** test that switching user changes the caller seen by the API.
3. (done) Enforcement: one access dependency per page router, plus Create plan and Sign plan.
   - **Check:** tests that a View role gets 403 on PATCH and a None role gets 403 on GET. Existing tests run as Admin and still pass.
4. (done) Roles API (Admin only): list, create, rename, delete roles, and `PUT /roles/{id}/permissions/{key}` to set one cell.
   - **Check:** tests for each route, the Admin lock and the 409 on deleting a role in use.
5. (done) UI: Admin section in the sidebar (shown only to users who can view it). Roles page with the role list (add, rename, delete) and the matrix. Each cell saves on change. Page column stays fixed when scrolling sideways; phones show one role at a time.
   - **Check:** drive it in headless Chrome, change a cell and see it saved.
6. (done) UI follows the role: hide None pages, View pages read-only, hide Sign without permission.
   - **Check:** as a read-only role, pages are read-only; as a role with None on a page, that page is hidden.

### 19. Admin: Users, Goal names, Clients (done)
Admin pages to manage users and their role, the goal-name catalog (focus area, label, prefix, active) and clients. Each is a row in the role matrix (`admin_users`, `admin_goal_names`, `admin_clients`) and an entry in the Admin sidebar section. One sub-step per page, each with API, tests, UI and a browser check.

1. (done) Users: list, add, edit (name, role, optional provider link), delete. Rules: one user per provider (409). There is always at least one Admin user: removing the Admin role from, or deleting, the last Admin user is 409. You cannot delete yourself (409). An unknown role or provider is 422.
   - **Check:** API tests for each rule; drive the page in headless Chrome, give a new user a role, sign in as them and see the role applied.
2. (done) Goal names: list, add, edit, turn active on or off. Rules: prefix unique ignoring case; focus area is free text with existing areas suggested; a name used on a plan cannot change focus area (409). A goal name used on a plan cannot be deleted (409), only turned inactive; inactive names leave existing goals alone but are not offered for new ones.
   - **Check:** API tests; an inactive name disappears from the goal pickers.
3. (done) Clients: list, add, edit the client record (name, date of birth, sex) shown on Information. Guardians and insurance stay seeded for now. A client with plans cannot be deleted (409).
   - **Check:** API tests; a new client can get a plan.

### 19a. Plans list (done)
The app's start page at `#/plans`: every plan grouped by client, with a "New plan" form, so plans can be found and created from the UI instead of by URL.

Rules:
- `GET /api/v2/treatment_plans/` lists plans (id, client, bay, status, owner, start date, signer) and the bay choices. Like reading one plan, it needs only a signed-in user; step 20 will narrow it to assigned clients.
- "New plan" (client and bay) uses the existing create route, so it follows the Create plan permission and needs a provider-linked user. The form is hidden without the permission and explains when the user is not a provider. After creating, the app opens the new plan.
- The sidebar gets a "Plans" link above the plan; on the Plans page the plan-specific parts (client, progress, sign, page list) are hidden. An empty address opens Plans instead of plan 1.

Sub-steps:
1. List API with tests (sweep updated: listing needs sign-in only, creating still needs the permission).
2. Plans page, sidebar link and start route; drive it in headless Chrome: create a plan for a new client and land on it.

### 20. Admin: Providers and Client assignment (done)
Defines which clients each user can see and work on. The role says what a user may do; the client rules say for which clients.

Rules (decided):
- A user sees a client when their role is the locked Admin, their role has the new "All clients" action (a matrix row, for billers, QA and similar), or their linked provider is clinically assigned to the client.
- A user edits a plan (on top of the role allowing Edit on the page) when they are Admin, own the plan, or are clinically assigned to its client. All-clients alone gives reading, not editing. This follows the spec.
- Clinical assignments are the existing `client_assignment` rows (provider, client, role: home BCBA, substitute BCBA, BT). They also feed the Information care team and the Treatment bay 3 text.

Sub-steps:
1. (done) Providers page (`admin_providers`): list, add, rename, active on or off. Inactive providers are not offered for new assignments or user links; existing ones stay. A provider that owns plans, has assignments or is linked to a user cannot be deleted (409).
   - **Check:** API tests; a new provider can be linked on Users.
2. (done) Client assignment page (`admin_assignments`): per client, add, change and remove assignments. One home BCBA per client; a provider appears once per client (409). Only active providers can be newly assigned.
   - **Check:** API tests; the Information care team shows the change.
3. (done) Enforcement: every plan route checks the client rules (reads and clone need "sees the plan", writes and sign need "edits the plan"; a clone belongs to its creator, so reading the source is enough); the plans list and the New plan client list show only visible clients. Assessment files are served through a checked route instead of the open `/uploads/` folder. The plan response says whether the caller can edit it.
   - **Check:** tests for each rule, and the route sweep extended with an unassigned user.
4. (done) UI follows the rules: plans the user cannot edit open read-only with a banner.
   - **Check:** drive it in headless Chrome as an assigned, an unassigned and an all-clients user.

### 21. Change history (done)
An audit log of who changed what and when, shown read-only on Admin - Change history (`admin_history`, None or View only).

Rules:
- Recorded: roles and their access cells, users, goal names, clients, providers, client assignments, and plans (created, cloned, signed). Plan page content is not recorded; it would drown the log and is not an admin change.
- One row per changed record: time (UTC), who (user id and name at the time), action (created, changed, deleted), what (record type, id and a readable label) and the changed fields with old and new values.
- Capture is automatic: a SQLAlchemy flush event records changes to the listed tables, using the signed-in user stored on the request's session. Writes with no signed-in user (seed, tests writing directly) are not recorded.
- The log is append-only: there are no routes to edit or delete it.

Sub-steps:
1. (done) Table, recording and `GET /api/v2/admin/history/` (newest first, filter by record type, page with `before`).
   - **Check:** tests that each recorded kind of change appears with who, what and old and new values, and that page edits and anonymous writes do not.
2. (done) Admin page: the newest changes as a list, a record-type filter, "Load older".
   - **Check:** drive it in headless Chrome after making changes on other admin pages.

### 22. Real login (done)
Replace the "sign in as" picker with email and password sign-in. The rest of the app keeps using the same current-user dependency.

Rules (decided):
- Users sign in with email and password. Passwords are stored only as Argon2 hashes and are at least 8 characters (changed from 12 by request).
- An admin sets a temporary password on Admin - Users; the user must choose their own before doing anything else. Resets work the same way and end that user's other sessions.
- A sign-in lasts 8 hours, with no idle limit. Sessions are rows in the database; the cookie holds a random token and only its SHA-256 is stored, so sign-out ends the session and a leaked database does not hand out sessions. The cookie is HttpOnly and SameSite=Strict; `TP_SECURE_COOKIE=1` adds Secure for HTTPS deployments.
- Five wrong passwords in a row lock the account for 15 minutes. Wrong email and wrong password give the same message.
- Passwords, hashes and lockout counters never appear in the change history.
- The first Admin's email and password are set from the command line (`uv run python -m app.set_password`), since nobody can sign in before that.
- Authenticator codes (MFA) are a later step.

Sub-steps:
1. (done) Data: user email (unique), password hash, must-change flag, lockout fields (added by `app/migrate.py`), a `user_session` table, Argon2 hashing, the `app.set_password` command, history excludes secrets.
   - **Check:** tests for hashing and the command, run on a database copy.
2. (done) Login API: sign in, sign out, who am I, change password, admin sets a temporary password, Users get an email field; the picker routes are removed and test helpers sign in with passwords.
   - **Check:** tests for wrong password, lockout, expiry, must-change gate, sign-out and reset ending sessions.
3. (done) UI: sign-in form, change-password screen, sign out, Users page email and "Set temporary password".
   - **Check:** drive it in headless Chrome end to end.
4. (done) README: first sign-in and the set-password command.

### 23. Authenticator codes (MFA)
Time-based codes from an authenticator app as a second sign-in step.

Rules (decided):
- Admin users must use MFA. An Admin without it is sent to set it up after the password step and can do nothing else first (like a forced password change). Other users may turn it on or off for themselves.
- Codes are standard TOTP (6 digits, 30 seconds, one step of clock drift either way), so any authenticator app works. Setup shows a QR code and the key as text; MFA is on only after the first correct code.
- With MFA on, a correct password starts a 5-minute half-signed-in session that can only enter a code, ask who am I, or sign out. A correct code makes it a full 8-hour session.
- A code cannot be used twice. Wrong codes count toward the same five-strikes lockout as wrong passwords.
- Lost phone: an Admin uses "Reset MFA" on Admin - Users, which turns it off and ends that user's sessions. The last Admin resets their own from the command line (`uv run python -m app.reset_mfa --user-id 1`).
- The MFA key is never in the change history; turning MFA on, off or resetting it is.
- The key is stored in plain text in the database: a leaked database still needs the password too, and the password hashes are Argon2.

Sub-steps:
1. (done) Data and code helpers: `pyotp` and `segno` (QR as SVG), user columns `mfa_secret`, `mfa_enabled`, `mfa_last_step`, session column `mfa_pending`, history excludes the key.
   - **Check:** tests for code checking, drift, replay and the history.
2. (done) API: setup and confirm, the code step at sign-in, the Admin setup gate, turn off (non-Admins, needs a code), Admin reset, `app.reset_mfa`. Test sign-in helpers handle the code.
   - **Check:** tests for each rule above.
3. UI: code step on the sign-in form, setup screen with the QR code, an account panel to turn it on or off, "Reset MFA" on Admin - Users.
   - **Check:** drive it in headless Chrome end to end.
4. README: MFA and the reset command.

## Decisions (spec conflicts)

Add entries as they come up during the build.

- PATCH: an omitted field keeps its stored value, including `not_attending_school`.
- Stage `reason` column is nullable.
- Crisis plans: deleting a behavior that has a crisis plan returns 409. The FK is enforced in the app, so plan deletes cascade cleanly.
- Same-day stage change: only the specific first transition each target type lists.
- The UI uses the API minimums wherever the form and API disagree.
- No login: every request acts as provider 1 (a BCBA). Plan status is a `status` string (`draft` or `signed`) instead of a status table.
- Tests use `httpx`; switching to `httpx2` (Starlette deprecation warning) was blocked by a permission prompt and is pending.
- Information status is always `completed`: it has no inputs. Its response adds `parents_guardians`, which the spec's response omits but the Parent/guardian card needs.
- Medication GET returns `no_medication: null` while unanswered (the spec's boolean cannot tell "not answered" from "unchecked"). Opening the new-medication form answers it as unchecked.
- Referral rows can be created partially (blank Add), like Medical diagnoses. Medication and Therapy use a draft form saved in one POST, because their create needs at least one field.
- A month/year date in the client's birth month counts as "after date of birth".
- Row timestamps (`date_row_created`, `date_row_updated`) are left out for now.
- Therapy with rows but the checkbox unanswered is an error, matching Medication (the spec's Therapy table leaves this case out).
- Education: Homeschool does not require school name or phone for completion (follows the form; the API rule would leave homeschool plans stuck in error). Checking "not attending" clears all other fields in the same PATCH.
- UI files are served with `Cache-Control: no-cache` so edits show up without a hard refresh.
- Family: members and siblings are created blank (Add) and filled field by field. A second primary caregiver is refused with 409. Duplicate list values are blocked by a unique constraint, not only app code. Choosing "Parent not a caregiver" clears the caregiver type in the same PATCH and hides the field.
- Child: an untouched Education page does not require a School slot. Schedule times are stored as naive UTC plus the slot's offset. Background items and list values are unique by database constraint.
- Assessment: readiness scores are Not ready 0, Somewhat 1, Ready 2; a section score sums its items. Unchecking telehealth clears the date and ratings in the same PATCH. Reassessment must be after the initial date. Visual files are stored in `uploads/` (`TP_UPLOAD_DIR`).
- Crisis: the behavior foreign key has no ON DELETE action; deleting a behavior with a crisis plan returns 409. Checked "not needed" completes the page as the spec says. The page response adds `available_behaviors` for the dropdown.
- Discharge: only Other takes an explanation, and it needs at least 4 characters. Changing it replaces the Other reason.
- Treatment: the bay 3 provisioning text is only required when a technician is assigned, as the spec says, so a bay 3 plan without one can complete.
- Goals: a goal_name catalog (focus area, label, prefix, active) is seeded. New targets start at New dated today. Changing a goal's method clears fields of the old method and applies defaults. Only the latest stage can be deleted, never the first New. BRG does not offer Percentage. Session counts are 1 to 100.
- Signing: `POST /api/v2/treatment_plans/{id}/sign/` with `{signature}` (the signer's typed full name, 2 to 255 characters) stores it in `treatment_plan.signature` and sets status `signed`. It is refused (422) unless all 13 pages are complete, which includes Goals, and refused (409) if already signed. There is no unsign. All 82 page write routes return 409 on a signed plan; reads still work.
- Roles: the spec lists read and write roles, but the app starts with only an Admin role with full access; Admin creates the others in the matrix. Each user has one role.
- Admin's access is not stored as cells. A `locked` role gets the highest allowed level for every key, so new pages are covered automatically and there are no Admin cells to lower.
- Users are their own table (`app_user`) with an optional provider link, since some roles (biller, guardian) are not providers.
- Development sign-in: `GET/PUT/DELETE /api/v2/session/`. The `tp_user` cookie holds the plain user id and is not signed, so it is for building only (step 22 replaces it). No cookie or an unknown user is 401 on routes that need a user. Signed out, the UI shows only the user picker; signed in, the sidebar has a "Signed in as" switcher. Tests sign in as the Admin user once per session.
- A new plan's `provider_id` is the signed-in user's provider. A user with no provider gets 422 on create.
- Access checks are attached in `main.py` when each page router is included (`PAGE_ROUTERS`, router to key). PCG, SAG and BRG all use the `goals` key. Reading a plan, its page statuses and the option lists needs only a signed-in user. A test sweeps every API route from the OpenAPI schema and expects 403 for a role with no access.
- Roles API at `/api/v2/admin/roles/`, guarded by the `admin_roles` key (view to list, edit to change). The list returns the matrix rows (`keys`: key, group, allowed levels) with every role, so the UI does not repeat them. A new role starts with no access. Role names are unique ignoring case, so "admin" cannot sit beside "Admin". Any change to the locked Admin role is 409.
- `GET /api/v2/session/` also returns `access`, the signed-in user's level for every key, so the UI can show only what the role allows. The current-user dependency lives in `app/access.py` (moved from `session.py` to avoid a circular import).
- Admin pages use the route `#/admin/{page}` and modules in `static/admin/`. The sidebar keeps the last plan; the Admin section lists only admin pages the user can view. Page and key labels live in `static/labels.js`.
- Roles screen: renames save on change, deleting asks to confirm, and a name clash shows next to the field instead of the failure banner. Matrix cells are tinted by level. A user with only View on Admin: Roles sees everything disabled.
- Known gap: files under `/uploads/` are served without an access check. Their names are random, but anyone with a link can open them. Fix with an access-checked download route when assignments (step 20) arrive.
- Actions store `edit` for Allowed and `none` for Not allowed, so one level column serves every key.
- Signed UI: the sidebar shows the signer, each page shows a read-only banner, every control is disabled, and add, delete and edit controls are hidden. Page navigation and Goals tabs still work.
- UI follows the role: the sidebar, pager and "Page N of M" list only pages the role can view. A link to a hidden plan page goes to the first visible page; a link to an admin page without access goes back to the plan. A role with no plan pages sees a short message. View pages reuse the signed-plan read-only mode (body class renamed `is-readonly`) with a "view but not change" banner. Sign plan is hidden without the permission. The progress card still counts all 13 pages, since signing needs all of them.
- Without View on Information, the sidebar shows "Client {id}" instead of the client's name.
- Users API at `/api/v2/admin/users/`, guarded by `admin_users`. The list also returns the roles and providers to choose from. Name and role cannot be set to null; the provider link can. The Users page saves each field on change; a refused change (last Admin, provider already linked) shows under the row and the field goes back to its saved value. The "Signed in as" switcher refreshes when users are added, renamed or deleted.
- Rules about who may do what live in the API. The Users page shows "You" instead of Delete on your own row, but the 409 is the real guard.
- Goal names API at `/api/v2/admin/goal_names/`, guarded by `admin_goal_names`. Focus areas are free text, because the sections are decided by area: Parent training is PCG, Behavior change is BRG, anything else is SAG. A name in use cannot change its focus area, since that would move existing goals into the wrong section. The list reports how many plan goals use each name.
- Prefix uniqueness is checked in the API, not by a database constraint, because `create_all` does not add constraints to the existing `goal_name` table.
- Clients API at `/api/v2/admin/clients/`, guarded by `admin_clients`. Names are required; date of birth (not in the future) and sex (free text, as the spec has it) are optional and can be cleared. Deleting a client without plans also deletes their guardians, insurance and assignments, since those rows cannot outlive the client. The list reports each client's plan count.
- (fixed by 19a) The UI had no way to create or pick a plan; the Plans page now does both.
- Plans page: `#/plans` is the start page (an empty address opens it). Plans and Admin pages hide the plan-specific sidebar (client, progress, sign, page list) and never load a plan, so a save there no longer refreshes plan 1's status. The sidebar "Plans" link and the brand both go to Plans.
- The plans list is ordered newest first and grouped by client in that order. It shows every v3 plan to any signed-in user until client assignment (step 20) narrows it.
- Clone: `POST /api/v2/treatment_plans/{id}/clone/` (Create plan permission, provider-linked user) makes a draft for the same client and bay, owned by the caller, with `parent_treatment_plan_id` set to the source. Signed plans can be cloned; that is how the next plan period starts. The copy is generic: every table whose foreign keys lead back to `treatment_plan` is copied parent first, and each foreign key to a copied row is re-pointed (crisis plans to copied behaviors, BRG links to copied SAG goals). New page tables are cloned with no extra code. Assessment visual files are copied too, so deleting a visual in the copy never removes the source's file. Stage history dates are copied as they are.
- The Plans page has "New plan from this" on every plan for users who can create plans.
- Schema changes to existing tables go in `app/migrate.py` (`ADDED_COLUMNS`), applied at startup and by the seed only when the column is missing, because `create_all` never alters existing tables. First entry: `provider.active`, default on.
- Providers API at `/api/v2/admin/providers/`, guarded by `admin_providers`. The list shows each provider's linked user, assignment count and plan count. Users offers only active providers plus any already linked, and refuses a new link to a turned-off provider (422); an existing link survives the provider being turned off.
- BCBA types: only Home BCBA and Substitute BCBA. The spec's bobbing BCBA is dropped by request: the Information response has no `bobbing_bcba` and assignments cannot use that role.
- Client assignment API at `/api/v2/admin/assignments/`, guarded by `admin_assignments`. Roles are Home BCBA, Substitute BCBA and BT. One Home BCBA per client and one assignment per provider per client are checked in the API (409); a database constraint would need a table rebuild on existing databases. Only active providers can be newly assigned; a turned-off provider's existing assignments stay and are marked "(turned off)".
- Client rules live in `app/access.py` (`sees_plan`, `edits_plan`, `sees_client`). The page access dependency applies them to every route with a `plan_id`; plan read, page statuses, sign and clone use `plan_reader` or `plan_editor`. A refused write says "You are not assigned to this client" when the user can read the plan, otherwise "You do not have access to this client". Creating a plan needs to see the client.
- "All clients" is an action row in the matrix, labeled "All clients (read)". It gives reading only; editing still needs Admin, ownership or assignment.
- Assessment files are served by `GET /uploads/{key}` with checks (Assessment view, then the plan's client), not a static folder. The role check comes first so an unauthorized caller learns nothing about which keys exist.
- `GET /treatment_plans/{id}/` adds `can_edit` for the caller.
- UI and client rules: a plan the user can read but not edit opens read-only with "You can view this plan but not change it: you are not assigned to this client", and Sign is hidden. A plan link the user cannot open (403) or that does not exist (404) shows a "Plan not available" page instead of the failure banner. A provider with no assigned clients is told so in the New plan card.
- Change history: `app/audit.py` listens to every session's `after_flush` and writes `audit_event` rows in the same transaction, so a change and its history entry commit or roll back together. `current_user` puts the user on `session.info`; FastAPI hands the same session to every dependency of a request. Plans record only creation, cloning and signing (status and signature), so page edits that touch `treatment_plan` columns (such as the medication answer) are not logged. Rows written with Core inserts (the page rows copied by clone) are not seen by the listener; the clone itself is recorded.
- Known limit: linked fields show ids (for example `provider_id`), not names.
- Login: `POST/GET/DELETE /api/v2/session/` and `POST /api/v2/session/password/`; admin resets at `POST /api/v2/admin/users/{id}/password/` (not for yourself). Sign-in compares against a dummy hash for unknown emails so both cases take about as long. Passwords are taken exactly as typed (no trimming). Any API 401 in the UI reloads to the sign-in form, so an expired session never shows the failure banner.
- New users must be given a role explicitly; the add form no longer defaults to one, because with only the Admin role it defaulted new users to Admin.
