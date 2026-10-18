const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
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

export async function structuredChatRequest(question) {
  const params = new URLSearchParams({ question });

  const res = await fetch(`${API_BASE}/structured/chat?${params.toString()}`, {
    method: "POST",
  });

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new Error(data.detail || "Failed to get structured data response");
  }

  return data;
}
export async function getOllamaInfo() {
  const res = await fetch(`${API_BASE}/ollama/info`)
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail || 'Failed to fetch model info')
  return data // {model, mode, is_cloud, url, structured_model, unstructured_model}
}

export { API_BASE };

export async function saveChatHistory(token, question, answer) {
  const res = await fetch(`${API_BASE}/chat/history`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({ question, answer }),
  });

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new Error(data.detail || "Failed to save chat history");
  }

  return data;
}

export async function getChatHistory(token) {
  const res = await fetch(`${API_BASE}/chat/history`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new Error(data.detail || "Failed to load chat history");
  }

  return data.history || [];
}


export async function unstructuredChatRequest(question, token) {
  const res = await fetch(`${API_BASE}/unstructured/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ question }),
  })

  const data = await res.json().catch(() => ({}))

  if (!res.ok) {
    throw new Error(
      typeof data.detail === 'string'
        ? data.detail
        : 'Failed to get unstructured chatbot response'
    )
  }

  return data
}


export async function automaticChatRequest(question, token) {
  const res = await fetch(`${API_BASE}/chat/auto`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ question }),
  })

  const data = await res.json().catch(() => ({}))

  if (!res.ok) {
    throw new Error(
      typeof data.detail === 'string'
        ? data.detail
        : 'Failed to get automatic chatbot response'
    )
  }

  return data
}
