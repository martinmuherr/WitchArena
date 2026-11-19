// Cliente de la API. Las cookies de sesión las gestiona el navegador (HttpOnly);
// el token CSRF se guarda en memoria y se manda en cada petición que cambia algo.
let csrf = null;

export function setCsrf(token) {
  csrf = token;
}

async function request(method, path, data) {
  const opts = { method, headers: {}, credentials: "same-origin" };
  if (method !== "GET") {
    opts.headers["Content-Type"] = "application/json";
    if (csrf) opts.headers["X-CSRF-Token"] = csrf;
    opts.body = JSON.stringify(data || {});
  }
  const res = await fetch(path, opts);
  let body = {};
  try {
    body = await res.json();
  } catch {
    body = {};
  }
  if (!res.ok) {
    const e = new Error(body.error || "Error " + res.status);
    e.status = res.status;
    throw e;
  }
  return body;
}

export const api = {
  get: (p) => request("GET", p),
  post: (p, d) => request("POST", p, d),
};
