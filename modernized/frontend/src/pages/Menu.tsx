import type { Page } from "../App";
import type { Session } from "../types";

const ITEMS: { page: Page; title: string; desc: string; adminOnly?: boolean }[] = [
  { page: "accounts", title: "Account View / Update", desc: "COACTVWC · COACTUPC" },
  { page: "cards", title: "Card List / View / Update", desc: "COCRDLIC · COCRDSLC · COCRDUPC" },
  { page: "transactions", title: "Transactions", desc: "COTRN00C · COTRN01C · COTRN02C" },
  { page: "billpay", title: "Bill Payment", desc: "COBIL00C" },
  { page: "report", title: "Transaction Report", desc: "CORPT00C / CBTRN03C" },
  { page: "statements", title: "Account Statements", desc: "CREASTMT / CBSTM03A" },
  { page: "authorizations", title: "Pending Authorizations", desc: "COPAUS0C/1C/2C" },
  { page: "users", title: "User Maintenance", desc: "COUSR00C–03C", adminOnly: true },
  { page: "types", title: "Tran Types & Categories", desc: "COTRTLIC · COTRTUPC", adminOnly: true },
  { page: "batch", title: "Batch Operations", desc: "POSTTRAN · INTCALC · COMBTRAN · DALYREJS", adminOnly: true },
];

export default function Menu({ session, go }: { session: Session; go: (p: Page) => void }) {
  const items = ITEMS.filter((i) => !i.adminOnly || session.user_type === "A");
  return (
    <div className="card">
      <h2>Main Menu — COMEN01C</h2>
      <div className="menu-grid">
        {items.map((i) => (
          <button key={i.page} className="menu-item" onClick={() => go(i.page)}>
            <h3>{i.title}</h3>
            <p>{i.desc}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
