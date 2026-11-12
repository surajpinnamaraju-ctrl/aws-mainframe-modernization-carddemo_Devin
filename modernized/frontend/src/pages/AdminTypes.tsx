import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { TranCategory, TranType } from "../types";

export default function AdminTypes() {
  const [types, setTypes] = useState<TranType[]>([]);
  const [cats, setCats] = useState<TranCategory[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [newType, setNewType] = useState({ cd: "", desc: "" });
  const [newCat, setNewCat] = useState({ type_cd: "", cat_cd: "", desc: "" });

  const load = async () => {
    try {
      setTypes(await api<TranType[]>("/api/admin/tran-types"));
      setCats(await api<TranCategory[]>("/api/admin/tran-categories"));
    } catch (e) { setError((e as Error).message); }
  };
  useEffect(() => { void load(); }, []);

  const call = async (path: string, method: string, body?: unknown) => {
    setError(""); setNotice("");
    try {
      await api(path, { method, body });
      setNotice("Done.");
      void load();
    } catch (e) { setError((e as Error).message); }
  };

  return (
    <div className="card">
      <h2>Transaction Types & Categories — COTRTLIC / COTRTUPC</h2>
      {error && <div className="error" role="alert">{error}</div>}
      {notice && <div className="notice">{notice}</div>}
      <h3 style={{ fontSize: 14 }}>Types</h3>
      <div className="toolbar">
        <input placeholder="CD" style={{ width: 60 }} value={newType.cd} maxLength={2}
               onChange={(e) => setNewType({ ...newType, cd: e.target.value })} />
        <input placeholder="Description" value={newType.desc}
               onChange={(e) => setNewType({ ...newType, desc: e.target.value })} />
        <button className="small" onClick={() =>
          void call(`/api/admin/tran-types?tran_type_cd=${newType.cd}`, "POST",
            { tran_type_desc: newType.desc })}>Add type</button>
      </div>
      <table>
        <thead><tr><th>Code</th><th>Description</th><th /></tr></thead>
        <tbody>
          {types.map((t) => (
            <tr key={t.tran_type_cd}>
              <td>{t.tran_type_cd}</td>
              <td>
                <input defaultValue={t.tran_type_desc} style={{ width: "80%" }}
                       onBlur={(e) => e.target.value !== t.tran_type_desc &&
                         void call(`/api/admin/tran-types/${t.tran_type_cd}`, "PUT",
                           { tran_type_desc: e.target.value })} />
              </td>
              <td><button className="link" onClick={() =>
                void call(`/api/admin/tran-types/${t.tran_type_cd}`, "DELETE")}>Delete</button></td>
            </tr>
          ))}
        </tbody>
      </table>
      <h3 style={{ fontSize: 14 }}>Categories</h3>
      <div className="toolbar">
        <input placeholder="Type" style={{ width: 60 }} value={newCat.type_cd} maxLength={2}
               onChange={(e) => setNewCat({ ...newCat, type_cd: e.target.value })} />
        <input placeholder="Cat" style={{ width: 60 }} value={newCat.cat_cd}
               onChange={(e) => setNewCat({ ...newCat, cat_cd: e.target.value })} />
        <input placeholder="Description" value={newCat.desc}
               onChange={(e) => setNewCat({ ...newCat, desc: e.target.value })} />
        <button className="small" onClick={() =>
          void call(`/api/admin/tran-categories?tran_type_cd=${newCat.type_cd}&tran_cat_cd=${newCat.cat_cd}`,
            "POST", { tran_cat_type_desc: newCat.desc })}>Add category</button>
      </div>
      <table>
        <thead><tr><th>Type</th><th>Cat</th><th>Description</th><th /></tr></thead>
        <tbody>
          {cats.map((c) => (
            <tr key={`${c.tran_type_cd}-${c.tran_cat_cd}`}>
              <td>{c.tran_type_cd}</td><td>{c.tran_cat_cd}</td>
              <td>
                <input defaultValue={c.tran_cat_type_desc} style={{ width: "80%" }}
                       onBlur={(e) => e.target.value !== c.tran_cat_type_desc &&
                         void call(`/api/admin/tran-categories/${c.tran_type_cd}/${c.tran_cat_cd}`,
                           "PUT", { tran_cat_type_desc: e.target.value })} />
              </td>
              <td><button className="link" onClick={() =>
                void call(`/api/admin/tran-categories/${c.tran_type_cd}/${c.tran_cat_cd}`,
                  "DELETE")}>Delete</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
