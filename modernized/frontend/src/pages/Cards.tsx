import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Card } from "../types";

export default function Cards() {
  const [acctId, setAcctId] = useState("");
  const [cards, setCards] = useState<Card[]>([]);
  const [selected, setSelected] = useState<Card | null>(null);
  const [form, setForm] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => { void load(""); }, []);

  const load = async (acct: string) => {
    setError("");
    try {
      setCards(await api<Card[]>(`/api/cards${acct ? `?acct_id=${acct}` : ""}`));
    } catch (e) { setError((e as Error).message); }
  };

  const save = async () => {
    if (!selected) return;
    setError(""); setNotice("");
    const body: Record<string, string> = {};
    for (const [k, v] of Object.entries(form)) if (v !== "") body[k] = v;
    try {
      const updated = await api<Card>(`/api/cards/${selected.card_num}`,
        { method: "PUT", body });
      setSelected(updated);
      setNotice("Card updated.");
      void load(acctId);
    } catch (e) { setError((e as Error).message); }
  };

  return (
    <div className="card">
      <h2>Cards — COCRDLIC / COCRDSLC / COCRDUPC</h2>
      {error && <div className="error" role="alert">{error}</div>}
      {notice && <div className="notice">{notice}</div>}
      <div className="toolbar">
        <label style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
          Account ID
          <input style={{ width: 120 }} value={acctId}
                 onChange={(e) => setAcctId(e.target.value)} />
        </label>
        <button className="small" onClick={() => void load(acctId)}>List</button>
      </div>
      <table>
        <thead><tr><th>Card #</th><th>Acct</th><th>Name</th><th>Expires</th><th>Status</th><th /></tr></thead>
        <tbody>
          {cards.map((c) => (
            <tr key={c.card_num}>
              <td>{c.card_num}</td><td>{c.acct_id}</td><td>{c.embossed_name}</td>
              <td>{c.expiration_date}</td><td>{c.active_status}</td>
              <td><button className="link" onClick={() => {
                setSelected(c);
                setForm({ embossed_name: c.embossed_name, active_status: c.active_status,
                          expiration_date: c.expiration_date || "" });
              }}>View/Edit</button></td>
            </tr>
          ))}
        </tbody>
      </table>
      {selected && (
        <form className="stack" style={{ marginTop: 16 }}
              onSubmit={(e) => { e.preventDefault(); void save(); }}>
          <h3 style={{ margin: 0, fontSize: 14 }}>Edit {selected.card_num}</h3>
          <label>Embossed name
            <input value={form.embossed_name}
                   onChange={(e) => setForm({ ...form, embossed_name: e.target.value })} />
          </label>
          <label>Active status
            <select value={form.active_status}
                    onChange={(e) => setForm({ ...form, active_status: e.target.value })}>
              <option value="Y">Y — Active</option>
              <option value="N">N — Inactive</option>
            </select>
          </label>
          <label>Expiration date (YYYY-MM-DD)
            <input value={form.expiration_date}
                   onChange={(e) => setForm({ ...form, expiration_date: e.target.value })} />
          </label>
          <button className="primary">Save</button>
        </form>
      )}
    </div>
  );
}
