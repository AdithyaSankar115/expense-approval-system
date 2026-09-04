const API_URL = "http://localhost:8000";

export async function login(email, password) {
  const res = await fetch(`${API_URL}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error("Login failed");
  return res.json();
}

export async function getMe(token) {
  const res = await fetch(`${API_URL}/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return res.json();
}

export async function createExpense(token, expense) {
  const res = await fetch(`${API_URL}/expenses`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(expense),
  });
  return res.json();
}

export async function submitExpense(token, id) {
  const res = await fetch(`${API_URL}/expenses/${id}/submit`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  return res.json();
}

export async function approveExpense(token, id, decision, comment) {
  const res = await fetch(`${API_URL}/expenses/${id}/approve`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ decision, comment }),
  });
  return res.json();
}

export async function getPendingExpenses(token) {
  const res = await fetch(`${API_URL}/expenses/pending`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return res.json();
}