import { useState } from "react";
import { api, fmtMoney } from "../api/client";
import type { Account } from "../types";

export default function BillPay() {
  const [acctId, setAcctId] = useState("");
  const [account, setAccount] = useState<Account | null>(null);
  const [confirm, setConfirm] = useState(false);
  const [result, setResult] = useState("");
  const [error, setError] = useState("");

  const view = async () => {
    setError(""); setResult("");
    try {
      setAccount(await api<Account>(`/api/accounts/${acctId}`));
    } catch (e) { setError((e as Error).message); setAccount(null); }
  };

  const pay = async () => {
    if (!account || String(account.acct_id) !== acctId.trim()) {
      setError("View the account's balance before paying it.");
      return;
    }
    setError(""); setResult("");
    try {
      const r = await api<{ paid_amount: string; new_balance: string }>(
        `/api/billpay/${account.acct_id}?confirm=true`, { method: "POST" });
      setResult(`Paid ${fmtMoney(r.paid_amount)} — new balance ${fmtMoney(r.new_balance)}.`);
      setAccount(null); setConfirm(false);
    } catch (e) { setError((e as Error).message); }
  };

  return (
    <div className="card">
      <h2>Bill Payment — COBIL00C</h2>
      {error && <div className="error" role="alert">{error}</div>}
      {result && <div className="notice">{result}</div>}
      <div className="toolbar">
        <label style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
          Account ID
          <input style={{ width: 120 }} value={acctId}
                 onChange={(e) => setAcctId(e.target.value)} />
        </label>
        <button className="small" onClick={() => void view()}>View balance</button>
      </div>
      {account && (
        <>
          <div className="kv"><b>Current balance</b><span>{fmtMoney(account.curr_bal)}</span></div>
          <label style={{ flexDirection: "row", alignItems: "center", gap: 8, marginTop: 12 }}>
            <input type="checkbox" checked={confirm}
                   onChange={(e) => setConfirm(e.target.checked)} />
            Pay full balance now? (COBIL00C confirmation)
          </label>
          <button className="primary" style={{ marginTop: 10 }}
                  disabled={!confirm} onClick={() => void pay()}>
            Confirm payment
          </button>
        </>
      )}
    </div>
  );
}
