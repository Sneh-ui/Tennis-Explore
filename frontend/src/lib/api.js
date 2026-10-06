const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

function authHeaders(token) {
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

export async function loginRequest({ email, password }) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new Error(data.detail || "Invalid email or password");
  }

  return data; // { access_token, token_type, user }
}

export async function fetchMe(token) {
  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Unauthorized");
  return res.json();
}

// Admin User CRUD
export async function listUsers(token) {
  const res = await fetch(`${API_BASE}/auth/users`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Failed to fetch users");
  return data;
}

export async function createUser(token, payload) {
  const res = await fetch(`${API_BASE}/auth/users`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Failed to create user");
  return data;
}

export async function updateUser(token, id, payload) {
  const res = await fetch(`${API_BASE}/auth/users/${id}`, {
    method: "PUT",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Failed to update user");
  return data;
}

export async function deleteUser(token, id) {
  const res = await fetch(`${API_BASE}/auth/users/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "Failed to delete user");
  }
}

export async function updateOwnPassword(token, payload) {
  const res = await fetch(`${API_BASE}/auth/me/password`, {
    method: "PUT",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Failed to update password");
  return data;
}

export { API_BASE };
