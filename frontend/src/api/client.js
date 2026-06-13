const TOKEN_KEY = "rag_token";
const USER_KEY = "rag_user";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser() {
  const raw = localStorage.getItem(USER_KEY);
  return raw ? JSON.parse(raw) : null;
}

export function setAuth(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

function authHeaders(extra = {}) {
  const token = getToken();
  const headers = { ...extra };
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

async function request(path, options = {}) {
  const headers = { ...options.headers };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(path, { ...options, headers });
  const text = await response.text();
  let data = null;
  if (text) {
    try { data = JSON.parse(text); }
    catch { data = { detail: text }; }
  }

  if (!response.ok) {
    const message = data?.detail || data?.message || `Request failed (${response.status})`;
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  return data;
}

// ── Auth ──

export async function register({ email, username, password }) {
  return request("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, username, password }),
  });
}

export async function login({ username, password }) {
  const body = new URLSearchParams({ username, password });
  return request("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
}

export async function fetchMe() {
  return request("/api/auth/me");
}

// ── Documents ──

export async function fetchDocuments() {
  return request("/api/documents");
}

export async function uploadDocument(file) {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch("/api/documents/upload", {
    method: "POST",
    headers: authHeaders(),
    body: form,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Upload failed");
  return data;
}

export async function deleteDocument(id) {
  const response = await fetch(`/api/documents/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Delete failed");
  }
}

// ── Chat ──

export async function queryDocuments({ query, documentIds, conversationId }) {
  return request("/api/chat/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      document_ids: documentIds?.length ? documentIds : null,
      conversation_id: conversationId || null,
    }),
  });
}

export function streamQuery({ query, documentIds }, onToken, onDone, onError) {
  const body = JSON.stringify({
    query,
    document_ids: documentIds?.length ? documentIds : null,
  });

  fetch("/api/chat/query/stream", {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body,
  }).then(async (response) => {
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      onError?.(new Error(data.detail || "Stream failed"));
      return;
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const payload = JSON.parse(line.slice(6));
            if (payload.token) onToken?.(payload.token);
            if (payload.answer) onDone?.(payload.answer);
          } catch {}
        }
      }
    }
    onDone?.();
  }).catch(onError);
}

// ── Conversations ──

export async function fetchConversations() {
  return request("/api/conversations");
}

export async function fetchConversation(id) {
  return request(`/api/conversations/${id}`);
}

export async function createConversation(title) {
  return request("/api/conversations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
}

export async function deleteConversation(id) {
  const response = await fetch(`/api/conversations/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Delete failed");
  }
}

// ── Usage ──

export async function fetchUsageSummary() {
  return request("/api/usage/summary");
}

export async function fetchUsageAnalytics(days = 30) {
  return request(`/api/usage/analytics?days=${days}`);
}

// ── Health ──

export async function fetchHealth() {
  return request("/health");
}
