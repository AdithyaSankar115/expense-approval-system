import { useState, useEffect } from "react";
import { login, getMe, createExpense, submitExpense, approveExpense, getPendingExpenses } from "./api";

function App() {
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [category, setCategory] = useState("");
  const [description, setDescription] = useState("");
  const [lastExpense, setLastExpense] = useState(null);

  const [pendingExpenses, setPendingExpenses] = useState([]);

  const canApprove = user?.role === "approver" || user?.role === "admin";

  useEffect(() => {
    if (token && canApprove) {
      loadPending();
    }
  }, [token, user]);

  async function loadPending() {
    const list = await getPendingExpenses(token);
    setPendingExpenses(list);
  }

  async function handleLogin(e) {
    e.preventDefault();
    setError("");
    try {
      const data = await login(email, password);
      const me = await getMe(data.access_token);
      setToken(data.access_token);
      setUser(me);
    } catch (err) {
      setError("Login failed. Check your email and password.");
    }
  }

  function handleLogout() {
    setToken(null);
    setUser(null);
    setPendingExpenses([]);
  }

  async function handleCreateExpense(e) {
    e.preventDefault();
    const expense = await createExpense(token, {
      amount: parseFloat(amount),
      currency,
      category,
      description,
    });
    setLastExpense(expense);
  }

  async function handleSubmitExpense() {
    if (!lastExpense) return;
    const updated = await submitExpense(token, lastExpense.id);
    setLastExpense(updated);
  }

  async function handleApprove(expenseId, decision) {
    try {
      const result = await approveExpense(token, expenseId, decision, "");
      if (result.detail) {
        alert(`Action failed: ${result.detail}`);
      } else {
        loadPending();
      }
    } catch (err) {
      alert("Action failed. See console for details.");
    }
  }

  if (!token) {
    return (
      <div style={{ maxWidth: 400, margin: "80px auto", fontFamily: "sans-serif" }}>
        <h2>Expense Approval System</h2>
        <form onSubmit={handleLogin}>
          <div style={{ marginBottom: 10 }}>
            <input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={{ width: "100%", padding: 8 }}
            />
          </div>
          <div style={{ marginBottom: 10 }}>
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={{ width: "100%", padding: 8 }}
            />
          </div>
          <button type="submit" style={{ width: "100%", padding: 10 }}>
            Log In
          </button>
        </form>
        {error && <p style={{ color: "red" }}>{error}</p>}
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 550, margin: "40px auto", fontFamily: "sans-serif" }}>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <h2>Expense Approval System</h2>
        <button onClick={handleLogout}>Log out</button>
      </div>
      <p>
        Logged in — role: <b>{user.role}</b>
      </p>

      <hr />

      <h3>Create an Expense</h3>
      <form onSubmit={handleCreateExpense}>
        <input placeholder="Amount" value={amount} onChange={(e) => setAmount(e.target.value)} style={{ display: "block", marginBottom: 8, width: "100%", padding: 6 }} />
        <input placeholder="Currency" value={currency} onChange={(e) => setCurrency(e.target.value)} style={{ display: "block", marginBottom: 8, width: "100%", padding: 6 }} />
        <input placeholder="Category" value={category} onChange={(e) => setCategory(e.target.value)} style={{ display: "block", marginBottom: 8, width: "100%", padding: 6 }} />
        <input placeholder="Description" value={description} onChange={(e) => setDescription(e.target.value)} style={{ display: "block", marginBottom: 8, width: "100%", padding: 6 }} />
        <button type="submit">Create Expense (Draft)</button>
      </form>

      {lastExpense && (
        <div style={{ marginTop: 12, padding: 10, background: "#f4f4f4" }}>
          <p>Created expense <b>{lastExpense.id}</b> — status: <b>{lastExpense.status}</b></p>
          {lastExpense.status === "draft" && (
            <button onClick={handleSubmitExpense}>Submit for Approval</button>
          )}
        </div>
      )}

      {canApprove && (
        <>
          <hr />
          <h3>Approval Queue ({pendingExpenses.length})</h3>
          {pendingExpenses.length === 0 && <p style={{ color: "#888" }}>Nothing pending right now.</p>}
          {pendingExpenses.map((exp) => (
            <div key={exp.id} style={{ border: "1px solid #ddd", padding: 10, marginBottom: 8, borderRadius: 4 }}>
              <p style={{ margin: 0 }}>
                <b>{exp.amount} {exp.currency}</b> — {exp.category}
              </p>
              <p style={{ margin: "4px 0", fontSize: 13, color: "#666" }}>{exp.description}</p>
              <button onClick={() => handleApprove(exp.id, "approved")}>Approve</button>{" "}
              <button onClick={() => handleApprove(exp.id, "rejected")}>Reject</button>
            </div>
          ))}
        </>
      )}
    </div>
  );
}

export default App;