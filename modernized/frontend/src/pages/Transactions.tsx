import { useEffect, useState } from "react";
import { api, fmtMoney } from "../api/client";
import type { Card, Transaction } from "../types";

interface Page { items: Transaction[]; total: number; page: number; page_size: number; }

export default function Transactions() {
  const [cardNum, setCardNum] = useState("");
  const [data, setData] = useState<Page | null>(null);
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Transaction | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [cards, setCards] = useState<Card[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [form, setForm] = useState({
    card_num: "", type_cd: "01", cat_cd: "1", source: "ONLINE",
    description: "", amount: "", merchant_id: "", merchant_name: "",
    merchant_city: "", merchant_zip: "",
  });

  const load = async (p = 1, card = cardNum) => {
    setError("");
    try {
      setData(await api<Page>(
        `/api/transactions?page=${p}&page_size=10${card ? `&card_num=${card}` : ""}`));
      setPage(p);
    } catch (e) { setError((e as Error).message); }
  };

  useEffect(() => {
    void load(1);
    api<Card[]>("/api/cards").then(setCards).catch(() => undefined);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const add = async () => {
    setError(""); setNotice("");
    try {
      const t = await api<Transaction>("/api/transactions", {
        method: "POST",
        body: {
          card_num: form.card_num, type_cd: form.type_cd,
          cat_cd: Number(form.cat_cd), source: form.source,
          description: form.description, amount: form.amount,
          merchant_id: Number(form.merchant_id || 0),
          merchant_name: form.merchant_name,
          merchant_city: form.merchant_city, merchant_zip: form.merchant_zip,
        },
      });
      setNotice(`Posted transaction ${t.tran_id}.`);
      setShowAdd(false);
      void load(1);
    } catch (e) { setError((e as Error).message); }
  };

  return (
    <div className="card">
      <h2>Transactions — COTRN00C/01C/02C</h2>
      {error && <div className="error" role="alert">{error}</div>}
      {notice && <div className="notice">{notice}</div>}
      <div className="toolbar">
        <label style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
          Card #
          <input style={{ width: 180 }} value={cardNum}
                 onChange={(e) => setCardNum(e.target.value)} />
        </label>
        <button className="small" onClick={() => void load(1)}>List</button>
        <button className="small" onClick={() => setShowAdd(!showAdd)}>Add transaction</button>
      </div>

      {showAdd && (
        <form className="stack" onSubmit={(e) => { e.preventDefault(); void add(); }}>
          <label>Card
            <select value={form.card_num}
                    onChange={(e) => setForm({ ...form, card_num: e.target.value })} required>
              <option value="">Select…</option>
              {cards.map((c) => <option key={c.card_num} value={c.card_num}>{c.card_num}</option>)}
            </select>
          </label>
          <label>Type
            <select value={form.type_cd}
                    onChange={(e) => setForm({ ...form, type_cd: e.target.value })}>
              <option value="01">01 Purchase</option>
              <option value="02">02 Payment</option>
              <option value="03">03 Refund</option>
              <option value="04">04 Cash Advance</option>
              <option value="05">05 Balance Transfer</option>
              <option value="06">06 Fee</option>
              <option value="07">07 Adjustment</option>
            </select>
          </label>
          <label>Category code<input value={form.cat_cd}
            onChange={(e) => setForm({ ...form, cat_cd: e.target.value })} /></label>
          <label>Description<input value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })} required /></label>
          <label>Amount<input value={form.amount}
            onChange={(e) => setForm({ ...form, amount: e.target.value })} required /></label>
          <label>Merchant name<input value={form.merchant_name}
            onChange={(e) => setForm({ ...form, merchant_name: e.target.value })} /></label>
          <button className="primary">Post</button>
        </form>
      )}

      {data && (
        <>
          <table>
            <thead><tr><th>ID</th><th>Date</th><th>Description</th><th>Amount</th><th /></tr></thead>
            <tbody>
              {data.items.map((t) => (
                <tr key={t.tran_id}>
                  <td>{t.tran_id}</td>
                  <td>{t.orig_ts.slice(0, 10)}</td>
                  <td>{t.description}</td>
                  <td>{fmtMoney(t.amount)}</td>
                  <td><button className="link"
                        onClick={() => setSelected(t)}>View</button></td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="toolbar" style={{ marginTop: 10 }}>
            <button className="small" disabled={page <= 1}
                    onClick={() => void load(page - 1)}>Prev</button>
            <span style={{ fontSize: 13 }}>Page {page} · {data.total} total</span>
            <button className="small" disabled={page * 10 >= data.total}
                    onClick={() => void load(page + 1)}>Next</button>
          </div>
        </>
      )}

      {selected && (
        <div className="card" style={{ background: "rgba(6,15,14,0.8)" }}>
          <h3 style={{ marginTop: 0, fontSize: 14 }}>Transaction {selected.tran_id}</h3>
          <div className="grid2">
            <div className="kv"><b>Card</b><span>{selected.card_num}</span></div>
            <div className="kv"><b>Type/Category</b><span>{selected.type_cd} / {selected.cat_cd}</span></div>
            <div className="kv"><b>Source</b><span>{selected.source}</span></div>
            <div className="kv"><b>Amount</b><span>{fmtMoney(selected.amount)}</span></div>
            <div className="kv"><b>Merchant</b><span>{selected.merchant_name} ({selected.merchant_id})</span></div>
            <div className="kv"><b>Location</b><span>{selected.merchant_city} {selected.merchant_zip}</span></div>
            <div className="kv"><b>Originated</b><span>{selected.orig_ts}</span></div>
            <div className="kv"><b>Processed</b><span>{selected.proc_ts}</span></div>
          </div>
        </div>
      )}
    </div>
  );
}
