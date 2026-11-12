import { useState } from "react";
import { api, fmtMoney } from "../api/client";
import type { TransactionReport } from "../types";

export default function Report() {
  const [start, setStart] = useState("2022-01-01");
  const [end, setEnd] = useState("2022-12-31");
  const [report, setReport] = useState<TransactionReport | null>(null);
  const [error, setError] = useState("");

  const run = async () => {
    setError("");
    try {
      setReport(await api<TransactionReport>(
        `/api/reports/transactions?start_date=${start}&end_date=${end}`));
    } catch (e) { setError((e as Error).message); setReport(null); }
  };

  return (
    <div className="card">
      <h2>Transaction Report — CORPT00C / CBTRN03C</h2>
      {error && <div className="error" role="alert">{error}</div>}
      <div className="toolbar">
        <label style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
          From <input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
        </label>
        <label style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
          To <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
        </label>
        <button className="primary" onClick={() => void run()}>Submit report</button>
      </div>
      {report && (
        <>
          <table>
            <thead>
              <tr><th>Tran ID</th><th>Acct</th><th>Card</th><th>Type</th>
                  <th>Category</th><th>Source</th><th>Amount</th><th>Date</th></tr>
            </thead>
            <tbody>
              {report.lines.map((l) => (
                <tr key={l.tran_id}>
                  <td>{l.tran_id}</td><td>{l.acct_id}</td><td>{l.card_num}</td>
                  <td>{l.type_cd} {l.type_desc}</td>
                  <td>{l.cat_cd} {l.cat_desc}</td>
                  <td>{l.source}</td>
                  <td>{fmtMoney(l.amount)}</td>
                  <td>{l.orig_ts.slice(0, 10)}</td>
                </tr>
              ))}
              <tr className="total-row">
                <td colSpan={6}>Grand total</td>
                <td>{fmtMoney(report.grand_total)}</td><td />
              </tr>
            </tbody>
          </table>
          {Object.keys(report.account_totals).length > 0 && (
            <>
              <h3 style={{ fontSize: 14 }}>Account totals</h3>
              <table>
                <thead><tr><th>Account</th><th>Total</th></tr></thead>
                <tbody>
                  {Object.entries(report.account_totals).map(([a, t]) => (
                    <tr key={a}><td>{a}</td><td>{fmtMoney(t)}</td></tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </>
      )}
    </div>
  );
}
