"use client";

import { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { EntityProvider, useEntities } from "@/lib/entity-context";

const NAV = [
  { href: "/", label: "Dashboard" },
  { href: "/accounts", label: "Chart of Accounts" },
  { href: "/opening-balances", label: "Opening Balances" },
  { href: "/journal", label: "Journal" },
  { href: "/import", label: "Import" },
  { href: "/reports", label: "Reports" },
];

const ADMIN_NAV = [
  { href: "/admin/entities", label: "Legal Entities" },
  { href: "/admin/users", label: "Users" },
  { href: "/admin/fx-rates", label: "FX Rates" },
];

function Shell({ children }: { children: ReactNode }) {
  const { user, logout, isAtLeast } = useAuth();
  const { entities, currentEntityId, setCurrentEntityId, isLoading } = useEntities();
  const pathname = usePathname();

  if (!user) return null;

  return (
    <div className="flex flex-1">
      <aside className="flex w-60 flex-col border-r border-slate-200 bg-white p-4">
        <div className="mb-6">
          <div className="text-sm font-semibold">Kodland Finance</div>
          <div className="text-xs text-slate-500">{user.email}</div>
          <div className="mt-1 inline-block rounded bg-slate-100 px-2 py-0.5 text-xs uppercase text-slate-600">
            {user.global_role}
          </div>
        </div>

        <div className="mb-4">
          <label className="mb-1 block text-xs font-medium text-slate-500">Legal Entity</label>
          {isLoading ? (
            <div className="text-xs text-slate-400">Loading...</div>
          ) : (
            <select
              className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
              value={currentEntityId ?? ""}
              onChange={(e) => setCurrentEntityId(Number(e.target.value))}
            >
              {entities.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.name} ({e.functional_currency})
                </option>
              ))}
            </select>
          )}
        </div>

        <nav className="flex flex-col gap-1 text-sm">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`rounded px-3 py-2 ${pathname === item.href ? "bg-slate-900 text-white" : "hover:bg-slate-100"}`}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        {isAtLeast("admin") && (
          <>
            <div className="mb-1 mt-6 text-xs font-medium uppercase text-slate-400">Admin</div>
            <nav className="flex flex-col gap-1 text-sm">
              {ADMIN_NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`rounded px-3 py-2 ${pathname === item.href ? "bg-slate-900 text-white" : "hover:bg-slate-100"}`}
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </>
        )}

        <button onClick={logout} className="mt-auto rounded px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50">
          Sign out
        </button>
      </aside>
      <main className="flex-1 overflow-auto p-6">{children}</main>
    </div>
  );
}

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <EntityProvider>
      <Shell>{children}</Shell>
    </EntityProvider>
  );
}
