import { useState } from "react";
import { api } from "../api/client";

const FILES = ["users", "customers", "accounts", "cards", "card_xrefs",
  "transactions", "daily_transactions", "tran_types", "tran_categories",
  "disclosure_groups", "tran_cat_balances", "pending_authorizations", "rejects"];

export default function Batch() {
  const [out, setOut] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [auditFile, setAuditFile] = useState("accounts");

  const run = async (name: string, path: string, method = "POST") => {
    setBusy(name); setError("");
    try {
      const r = await api(path, { method });
      setOut(JSON.stringify(r, null, 2));
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(""); }
  };

  return (
    <div className="card">
      <h2>Batch Operations</h2>
      {error && <div className="error" role="alert">{error}</div>}
      <div className="toolbar">
        <button className="small" disabled={!!busy}
                onClick={() => void run("post", "/api/batch/post-daily")}>
          {busy === "post" ? "Posting…" : "Run POSTTRAN (daily posting)"}
        </button>
        <button className="small" disabled={!!busy}
                onClick={() => void run("int", "/api/batch/interest")}>
          {busy === "int" ? "Computing…" : "Run INTCALC (interest)"}
        </button>
        <button className="small" disabled={!!busy}
                onClick={() => void run("purge", "/api/batch/purge-expired")}>
          {busy === "purge" ? "Purging…" : "Purge expired authorizations"}
        </button>
        <button className="small" disabled={!!busy}
                onClick={() => void run("rej", "/api/batch/rejects", "GET")}>
          DALYREJS rejects
        </button>
        <button className="small" disabled={!!busy}
                onClick={() => void run("exp", "/api/batch/export", "GET")}>
          CBEXPORT dump
        </button>
      </div>
      <div className="toolbar">
        <label style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
          Audit file (COAUDITC)
          <select value={auditFile} onChange={(e) => setAuditFile(e.target.value)}>
            {FILES.map((f) => <option key={f} value={f}>{f}</option>)}
          </select>
        </label>
        <button className="small" disabled={!!busy}
                onClick={() => void run("audit", `/api/batch/audit/${auditFile}`, "GET")}>
          Dump
        </button>
      </div>
      {out && <pre className="out">{out}</pre>}
    </div>
  );
}
