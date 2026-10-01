const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api/v1";
let session = JSON.parse(sessionStorage.getItem("focus-session") || "null");
let refreshPromise;
export function getSession() {
  return session;
}
export function saveSession(value) {
  session = value;
  value
    ? sessionStorage.setItem("focus-session", JSON.stringify(value))
    : sessionStorage.removeItem("focus-session");
}
export async function api(path, options = {}, retry = true) {
  const response = await fetch(BASE + path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(session ? { Authorization: `Bearer ${session.access}` } : {}),
      ...options.headers,
    },
    ...(options.body ? { body: JSON.stringify(options.body) } : {}),
  });
  if (
    response.status === 401 &&
    retry &&
    session?.refresh &&
    !["/auth/login", "/auth/register", "/auth/refresh"].includes(path)
  ) {
    refreshPromise ||= api(
      "/auth/refresh",
      { method: "POST", body: { refresh: session.refresh } },
      false,
    )
      .then(saveSession)
      .finally(() => {
        refreshPromise = null;
      });
    await refreshPromise;
    return api(path, options, false);
  }
  const result = await response.json();
  if (!response.ok) {
    const error = result.error;
    throw new Error(
      error?.message === "Please check your input."
        ? JSON.stringify(error.details)
        : error?.message || "Request failed",
    );
  }
  return result.data;
}
