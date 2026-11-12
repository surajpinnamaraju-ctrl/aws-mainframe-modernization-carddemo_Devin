import { useState } from "react";
import { api, setToken } from "./api/client";
import type { Session } from "./types";
import Login from "./pages/Login";
import Menu from "./pages/Menu";
import Accounts from "./pages/Accounts";
import Cards from "./pages/Cards";
import Transactions from "./pages/Transactions";
import Report from "./pages/Report";
import BillPay from "./pages/BillPay";
import Authorizations from "./pages/Authorizations";
import AdminUsers from "./pages/AdminUsers";
import AdminTypes from "./pages/AdminTypes";
import Batch from "./pages/Batch";
import Statements from "./pages/Statements";

export type Page =
  | "menu" | "accounts" | "cards" | "transactions" | "report"
  | "billpay" | "authorizations" | "users" | "types" | "batch"
  | "statements";

const NAV: { key: Page; label: string; adminOnly?: boolean }[] = [
  { key: "menu", label: "Menu" },
  { key: "accounts", label: "Accounts" },
  { key: "cards", label: "Cards" },
  { key: "transactions", label: "Transactions" },
  { key: "billpay", label: "Bill Pay" },
  { key: "report", label: "Reports" },
  { key: "statements", label: "Statements" },
  { key: "authorizations", label: "Authorizations" },
  { key: "users", label: "User Admin", adminOnly: true },
  { key: "types", label: "Types & Categories", adminOnly: true },
  { key: "batch", label: "Batch", adminOnly: true },
];

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [page, setPage] = useState<Page>("menu");

  if (!session) {
    return <Login onLogin={(s) => { setSession(s); setToken(s.token); }} />;
  }

  const logout = async () => {
    try { await api("/api/auth/logout", { method: "POST" }); } catch { /* ignore */ }
    setToken(null);
    setSession(null);
    setPage("menu");
  };

  const nav = NAV.filter((n) => !n.adminOnly || session.user_type === "A");

  const pages: Record<Page, JSX.Element> = {
    menu: <Menu session={session} go={setPage} />,
    accounts: <Accounts />,
    cards: <Cards />,
    transactions: <Transactions />,
    report: <Report />,
    billpay: <BillPay />,
    authorizations: <Authorizations />,
    users: <AdminUsers />,
    types: <AdminTypes />,
    batch: <Batch />,
    statements: <Statements />,
  };

  return (
    <>
      <header>
        <div className="brand">
          <h1>CARDDEMO</h1>
          <div className="tagline">Modernized mainframe</div>
        </div>
        <nav>
          {nav.map((n) => (
            <button key={n.key} className={page === n.key ? "active" : ""}
                    onClick={() => setPage(n.key)}>{n.label}</button>
          ))}
        </nav>
        <span className="who">{session.first_name} {session.last_name} · {session.user_id}</span>
        <button className="logout" onClick={logout}>Sign off</button>
      </header>
      <main>{pages[page]}</main>
    </>
  );
}
