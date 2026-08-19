"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { useEntities } from "@/lib/entity-context";

export default function DashboardPage() {
  const { user, isAtLeast } = useAuth();
  const { entities, isLoading } = useEntities();

  return (
    <div>
      <h1 className="mb-1 text-2xl font-semibold">Dashboard</h1>
      <p className="mb-6 text-sm text-slate-500">Signed in as {user?.full_name || user?.email} ({user?.global_role})</p>

      {isLoading ? (
        <p className="text-sm text-slate-500">Loading legal entities...</p>
      ) : entities.length === 0 ? (
        <div className="rounded border border-dashed border-slate-300 p-6 text-sm text-slate-500">
          No legal entities yet.{" "}
          {isAtLeast("admin") ? (
            <Link href="/admin/entities" className="text-slate-900 underline">
              Create one
            </Link>
          ) : (
            "Ask an administrator to create one."
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {entities.map((e) => (
            <div key={e.id} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <div className="font-medium">{e.name}</div>
              <div className="text-sm text-slate-500">{e.country}</div>
              <div className="mt-2 inline-block rounded bg-slate-100 px-2 py-0.5 text-xs">{e.functional_currency}</div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Link href="/accounts" className="rounded border border-slate-200 bg-white p-4 text-center text-sm hover:bg-slate-50">
          Chart of Accounts
        </Link>
        <Link href="/journal" className="rounded border border-slate-200 bg-white p-4 text-center text-sm hover:bg-slate-50">
          Journal Entries
        </Link>
        <Link href="/import" className="rounded border border-slate-200 bg-white p-4 text-center text-sm hover:bg-slate-50">
          Import Wizard
        </Link>
        <Link href="/reports" className="rounded border border-slate-200 bg-white p-4 text-center text-sm hover:bg-slate-50">
          Reports
        </Link>
      </div>
    </div>
  );
}
