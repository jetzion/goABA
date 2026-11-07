/** Thin fetch helpers for the v2 treatment plan API. */

const BASE = "/api/v2/treatment_plans";
const SESSION = "/api/v2/session";

async function request(method, path, body, base = BASE) {
  const response = await fetch(base + path, {
    method,
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (response.status === 401 && base !== SESSION) {
    location.reload();
    return new Promise(() => {});
  }
  if (response.status === 204) return null;
  const data = await response.json();
  if (!response.ok) throw Object.assign(new Error("Request failed"), { status: response.status, data });
  return data;
}

export const api = {
  get: (path) => request("GET", path),
  post: (path, body) => request("POST", path, body),
  patch: (path, body) => request("PATCH", path, body),
  del: (path) => request("DELETE", path),
};

/** Admin API: roles, users, catalog, clients, providers, assignments, history. */
export const adminApi = {
  get: (path) => request("GET", path, undefined, "/api/v2/admin"),
  post: (path, body) => request("POST", path, body, "/api/v2/admin"),
  patch: (path, body) => request("PATCH", path, body, "/api/v2/admin"),
  put: (path, body) => request("PUT", path, body, "/api/v2/admin"),
  del: (path) => request("DELETE", path, undefined, "/api/v2/admin"),
};

/** Sign-in: who am I, sign in and out, the authenticator code, change your own password. A 401 here is an answer, not an expiry. */
export const session = {
  get: () => request("GET", "/", undefined, SESSION),
  signIn: (email, password) => request("POST", "/", { email, password }, SESSION),
  signOut: () => request("DELETE", "/", undefined, SESSION),
  enterCode: (code) => request("POST", "/mfa/", { code }, SESSION),
  startMfaSetup: () => request("POST", "/mfa/setup/", {}, SESSION),
  enableMfa: (code) => request("POST", "/mfa/enable/", { code }, SESSION),
  disableMfa: (code) => request("POST", "/mfa/disable/", { code }, SESSION),
  changePassword: (current, next) => request("POST", "/password/", { current_password: current, new_password: next }, SESSION),
};
