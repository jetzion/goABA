/** Small rendering helpers shared by page modules. */

export function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

export function dl(pairs) {
  return `<dl class="pairs">${pairs.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${v ? esc(v) : '<span class="muted">-</span>'}</dd>`).join("")}</dl>`;
}

/** A form section: title and optional hint on the left, content on the right. */
export function card(title, body, hint = "") {
  return `<section class="section">
    <header class="section-head"><h2>${esc(title)}</h2>${hint ? `<p>${esc(hint)}</p>` : ""}</header>
    <div class="section-body">${body}</div>
  </section>`;
}

/** Run a save; show a 409 or 422 in errEl and return undefined. Anything else goes to the failure banner. */
export async function tryInline(errEl, action, fallback = "Check this value.") {
  errEl.textContent = "";
  try {
    return await action();
  } catch (err) {
    if (![409, 422].includes(err.status)) throw err;
    const detail = err.data?.detail;
    errEl.textContent = typeof detail === "string" ? detail : fallback;
    dispatchEvent(new Event("tp:invalid"));
    return undefined;
  }
}

/** Re-render a page into a fresh element so old event listeners are dropped. */
export async function rerender(root, render, planId) {
  const fresh = document.createElement("div");
  root.replaceWith(fresh);
  await render(fresh, planId);
  dispatchEvent(new Event("tp:saved"));
}
