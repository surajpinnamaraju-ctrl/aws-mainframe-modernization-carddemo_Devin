import { useState } from "react";
import { api, fmtMoney } from "../api/client";
import type { Statement } from "../types";

export default function Statements() {
  const [acctId, setAcctId] = useState("");
  const [stmt, setStmt] = useState<Statement | null>(null);
  const [error, setError] = useState("");

  const load = async () => {
    setError("");
    try {
      setStmt(await api<Statement>(`/api/statements/${acctId}`));
    } catch (e) { setError((e as Error).message); setStmt(null); }
  };

  return (
    <div className="card">
      <h2>Account Statement — CREASTMT / CBSTM03A</h2>
      {error && <div className="error" role="alert">{error}</div>}
      <div className="toolbar">
        <label style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
          Account ID
          <input style={{ width: 120 }} value={acctId}
                 onChange={(e) => setAcctId(e.target.value)} />
        </label>
        <button className="primary" onClick={() => void load()}>Generate</button>
      </div>
      {stmt && (
        <>
          <div className="grid2">
            <div className="kv"><b>Account</b><span>{stmt.acct_id}</span></div>
            <div className="kv"><b>Card</b><span>{stmt.card_num}</span></div>
            <div className="kv"><b>Customer</b><span>{stmt.cust_name}</span></div>
            <div className="kv"><b>FICO</b><span>{stmt.fico_score}</span></div>
            <div className="kv"><b>Address</b><span>{stmt.address.join(", ")}</span></div>
          </div>
          <table style={{ marginTop: 12 }}>
            <thead><tr><th>Tran ID</th><th>Date</th><th>Description</th><th>Amount</th></tr></thead>
            <tbody>
              {stmt.lines.map((t) => (
                <tr key={t.tran_id}>
                  <td>{t.tran_id}</td><td>{t.orig_ts.slice(0, 10)}</td>
                  <td>{t.description}</td><td>{fmtMoney(t.amount)}</td>
                </tr>
              ))}
              <tr className="total-row">
                <td colSpan={3}>Total expenses</td>
                <td>{fmtMoney(stmt.total_expenses)}</td>
              </tr>
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
