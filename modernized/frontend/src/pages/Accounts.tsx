import { useEffect, useState } from "react";
import { api, fmtMoney } from "../api/client";
import type { Account } from "../types";

export default function Accounts() {
  const [ids, setIds] = useState<number[]>([]);
  const [selected, setSelected] = useState<Account | null>(null);
  const [form, setForm] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    api<number[]>("/api/accounts").then(setIds).catch((e) => setError(e.message));
  }, []);

  const view = async (id: number) => {
    setError(""); setNotice("");
    try {
      const a = await api<Account>(`/api/accounts/${id}`);
      setSelected(a);
      setForm({
        active_status: a.active_status,
        credit_limit: a.credit_limit,
        cash_credit_limit: a.cash_credit_limit,
        expiration_date: a.expiration_date || "",
        reissue_date: a.reissue_date || "",
        addr_zip: a.addr_zip || "",
        group_id: a.group_id || "",
      });
    } catch (e) { setError((e as Error).message); }
  };

  const save = async () => {
    if (!selected) return;
    setError(""); setNotice("");
    const body: Record<string, string> = {};
    for (const [k, v] of Object.entries(form)) if (v !== "") body[k] = v;
    try {
      const updated = await api<Account>(`/api/accounts/${selected.acct_id}`, {
        method: "PUT", body,
      });
      setSelected(updated);
      setNotice("Account updated.");
    } catch (e) { setError((e as Error).message); }
  };

  return (
    <div className="card">
      <h2>Accounts — COACTVWC / COACTUPC</h2>
      {error && <div className="error" role="alert">{error}</div>}
      {notice && <div className="notice">{notice}</div>}
      <div className="toolbar">
        <label style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
          Account
          <select onChange={(e) => e.target.value && view(Number(e.target.value))}
                  defaultValue="">
            <option value="">Select…</option>
            {ids.map((i) => <option key={i} value={i}>{i}</option>)}
          </select>
        </label>
      </div>
      {selected && (
        <>
          <div className="grid2">
            <div className="kv"><b>Account ID</b><span>{selected.acct_id}</span></div>
            <div className="kv"><b>Status</b><span>{selected.active_status === "Y" ? "Active" : "Inactive"}</span></div>
            <div className="kv"><b>Customer</b><span>{selected.cust_first_name} {selected.cust_last_name}</span></div>
            <div className="kv"><b>Card</b><span>{selected.card_num}</span></div>
            <div className="kv"><b>Balance</b><span>{fmtMoney(selected.curr_bal)}</span></div>
            <div className="kv"><b>Cycle credit / debit</b><span>{fmtMoney(selected.curr_cyc_credit)} / {fmtMoney(selected.curr_cyc_debit)}</span></div>
            <div className="kv"><b>Open date</b><span>{selected.open_date}</span></div>
          </div>
          <h3 style={{ fontSize: 14, marginTop: 18 }}>Update</h3>
          <form className="stack" onSubmit={(e) => { e.preventDefault(); void save(); }}>
            <label>Active status
              <select value={form.active_status}
                      onChange={(e) => setForm({ ...form, active_status: e.target.value })}>
                <option value="Y">Y — Active</option>
                <option value="N">N — Inactive</option>
              </select>
            </label>
            <label>Credit limit
              <input value={form.credit_limit}
                     onChange={(e) => setForm({ ...form, credit_limit: e.target.value })} />
            </label>
            <label>Cash credit limit
              <input value={form.cash_credit_limit}
                     onChange={(e) => setForm({ ...form, cash_credit_limit: e.target.value })} />
            </label>
            <label>Expiration date (YYYY-MM-DD)
              <input value={form.expiration_date}
                     onChange={(e) => setForm({ ...form, expiration_date: e.target.value })} />
            </label>
            <label>ZIP
              <input value={form.addr_zip}
                     onChange={(e) => setForm({ ...form, addr_zip: e.target.value })} />
            </label>
            <button className="primary">Save</button>
          </form>
        </>
      )}
    </div>
  );
}
