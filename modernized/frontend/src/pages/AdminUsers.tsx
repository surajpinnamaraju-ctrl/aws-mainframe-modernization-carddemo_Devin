import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { User } from "../types";

export default function AdminUsers() {
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [editing, setEditing] = useState<string | null>(null);
  const [form, setForm] = useState({ first_name: "", last_name: "",
    password: "", user_type: "U" });
  const [newId, setNewId] = useState("");

  const load = async () => {
    try { setUsers(await api<User[]>("/api/admin/users")); }
    catch (e) { setError((e as Error).message); }
  };
  useEffect(() => { void load(); }, []);

  const save = async (id: string | null) => {
    setError(""); setNotice("");
    try {
      if (id) {
        await api(`/api/admin/users/${id}`, { method: "PUT", body: form });
        setNotice(`Updated ${id}.`);
      } else {
        await api(`/api/admin/users?user_id=${newId}`,
          { method: "POST", body: form });
        setNotice(`Added ${newId}.`);
        setNewId("");
      }
      setEditing(null); void load();
    } catch (e) { setError((e as Error).message); }
  };

  const del = async (id: string) => {
    setError(""); setNotice("");
    try {
      await api(`/api/admin/users/${id}`, { method: "DELETE" });
      setNotice(`Deleted ${id}.`); void load();
    } catch (e) { setError((e as Error).message); }
  };

  const rowForm = (id: string | null) => (
    <form className="stack" style={{ margin: "8px 0" }}
          onSubmit={(e) => { e.preventDefault(); void save(id); }}>
      {!id && <label>User ID<input value={newId} maxLength={8}
        onChange={(e) => setNewId(e.target.value.toUpperCase())} required /></label>}
      <label>First name<input value={form.first_name}
        onChange={(e) => setForm({ ...form, first_name: e.target.value })} required /></label>
      <label>Last name<input value={form.last_name}
        onChange={(e) => setForm({ ...form, last_name: e.target.value })} required /></label>
      <label>Password<input value={form.password} maxLength={8}
        onChange={(e) => setForm({ ...form, password: e.target.value })} required /></label>
      <label>Type
        <select value={form.user_type}
                onChange={(e) => setForm({ ...form, user_type: e.target.value as "A" | "U" })}>
          <option value="U">U — Regular</option>
          <option value="A">A — Admin</option>
        </select>
      </label>
      <div className="toolbar">
        <button className="primary">Save</button>
        <button type="button" className="small" onClick={() => setEditing(null)}>Cancel</button>
      </div>
    </form>
  );

  return (
    <div className="card">
      <h2>User Maintenance — COUSR00C/01C/02C/03C</h2>
      {error && <div className="error" role="alert">{error}</div>}
      {notice && <div className="notice">{notice}</div>}
      <div className="toolbar">
        <button className="small" onClick={() => {
          setEditing("new");
          setForm({ first_name: "", last_name: "", password: "", user_type: "U" });
        }}>Add user</button>
      </div>
      {editing === "new" && rowForm(null)}
      <table>
        <thead><tr><th>User ID</th><th>Name</th><th>Type</th><th /></tr></thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.user_id}>
              <td>{u.user_id}</td>
              <td>{u.first_name} {u.last_name}</td>
              <td>{u.user_type === "A" ? "Admin" : "Regular"}</td>
              <td>
                <button className="link" onClick={() => {
                  setEditing(u.user_id);
                  setForm({ first_name: u.first_name, last_name: u.last_name,
                            password: "", user_type: u.user_type });
                }}>Update</button>{" "}
                <button className="link" onClick={() => void del(u.user_id)}>Delete</button>
                {editing === u.user_id && rowForm(u.user_id)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
