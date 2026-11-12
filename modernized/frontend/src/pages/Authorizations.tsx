import { useEffect, useState } from "react";
import { api, fmtMoney } from "../api/client";
import type { Authorization, Card } from "../types";

export default function Authorizations() {
  const [auths, setAuths] = useState<Authorization[]>([]);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [cards, setCards] = useState<Card[]>([]);
  const [form, setForm] = useState({ card_num: "", amount: "",
    merchant_name: "" });

  const load = async (s = status) => {
    try {
      setAuths(await api<Authorization[]>(
        `/api/authorizations${s ? `?status=${s}` : ""}`));
    } catch (e) { setError((e as Error).message); }
  };
  useEffect(() => {
    void load("");
    api<Card[]>("/api/cards").then(setCards).catch(() => undefined);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const request = async () => {
    setError(""); setNotice("");
    try {
      const a = await api<Authorization>("/api/authorizations", {
        method: "POST",
        body: { card_num: form.card_num, amount: Number(form.amount),
                merchant_name: form.merchant_name },
      });
      setNotice(`Authorization ${a.auth_id}: ${a.status}.`);
      void load();
    } catch (e) { setError((e as Error).message); }
  };

  return (
    <div className="card">
      <h2>Pending Authorizations — COPAUS0C/1C/2C</h2>
      {error && <div className="error" role="alert">{error}</div>}
      {notice && <div className="notice">{notice}</div>}
      <div className="toolbar">
        <select value={status} onChange={(e) => { setStatus(e.target.value); void load(e.target.value); }}>
          <option value="">All statuses</option>
          <option value="PENDING">Pending</option>
          <option value="APPROVED">Approved</option>
          <option value="DECLINED">Declined</option>
          <option value="EXPIRED">Expired</option>
        </select>
      </div>
      <form className="stack" onSubmit={(e) => { e.preventDefault(); void request(); }}>
        <h3 style={{ margin: 0, fontSize: 14 }}>Request authorization</h3>
        <label>Card
          <select value={form.card_num} required
                  onChange={(e) => setForm({ ...form, card_num: e.target.value })}>
            <option value="">Select…</option>
            {cards.map((c) => <option key={c.card_num} value={c.card_num}>{c.card_num}</option>)}
          </select>
        </label>
        <label>Amount<input value={form.amount} required
          onChange={(e) => setForm({ ...form, amount: e.target.value })} /></label>
        <label>Merchant<input value={form.merchant_name}
          onChange={(e) => setForm({ ...form, merchant_name: e.target.value })} /></label>
        <button className="primary">Request</button>
      </form>
      <table style={{ marginTop: 14 }}>
        <thead><tr><th>Auth ID</th><th>Card</th><th>Acct</th><th>Merchant</th>
                <th>Amount</th><th>Status</th><th>Expires</th></tr></thead>
        <tbody>
          {auths.map((a) => (
            <tr key={a.auth_id}>
              <td>{a.auth_id}</td><td>{a.card_num}</td><td>{a.acct_id}</td>
              <td>{a.merchant_name}</td><td>{fmtMoney(a.amount)}</td>
              <td>{a.status}</td><td>{a.expiry_ts?.slice(0, 10)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
