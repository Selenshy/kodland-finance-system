"use client";

import { Fragment, ReactNode, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import { ChartOfAccount, AccountType } from "@/lib/types";
import { useEntities } from "@/lib/entity-context";
import { useAuth } from "@/lib/auth-context";

const ACCOUNT_TYPES: AccountType[] = ["asset", "liability", "equity", "income", "expense"];

const emptyForm = {
  code: "",
  name: "",
  account_type: "asset" as AccountType,
  report_line: "",
  is_cash: false,
  is_postable: true,
};

export default function AccountsPage() {
  const { currentEntityId, currentEntity } = useEntities();
  const { isAtLeast } = useAuth();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [form, setForm] = useState(emptyForm);
  const [importResult, setImportResult] = useState<string | null>(null);

  const canEdit = isAtLeast("admin");

  const { data: accounts = [], isLoading } = useQuery({
    queryKey: ["accounts", currentEntityId],
    queryFn: () => apiRequest<ChartOfAccount[]>(`/api/legal-entities/${currentEntityId}/accounts`),
    enabled: !!currentEntityId,
  });

  const byParent = useMemo(() => {
    const map = new Map<number | null, ChartOfAccount[]>();
    for (const a of accounts) {
      const key = a.parent_id;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(a);
    }
    return map;
  }, [accounts]);

  const createMutation = useMutation({
    mutationFn: (payload: typeof emptyForm) =>
      apiRequest(`/api/legal-entities/${currentEntityId}/accounts`, { method: "POST", body: payload }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts", currentEntityId] });
      setForm(emptyForm);
    },
  });

  const importMutation = useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      return apiRequest<{ created: number; updated: number; errors: string[] }>(
        `/api/legal-entities/${currentEntityId}/accounts/import`,
        { method: "POST", body: fd, isForm: true }
      );
    },
    onSuccess: (res) => {
      setImportResult(`Created ${res.created}, updated ${res.updated}, ${res.errors.length} errors.`);
      queryClient.invalidateQueries({ queryKey: ["accounts", currentEntityId] });
    },
  });

  function renderTree(parentId: number | null, depth: number): ReactNode {
    const children = byParent.get(parentId) || [];
    return children
      .sort((a, b) => a.code.localeCompare(b.code))
      .map((a) => (
        <Fragment key={a.id}>
          <tr className="border-b border-slate-100">
            <td className="py-1.5 pr-4" style={{ paddingLeft: `${depth * 20}px` }}>
              {a.code}
            </td>
            <td className="py-1.5 pr-4">{a.name}</td>
            <td className="py-1.5 pr-4 capitalize">{a.account_type}</td>
            <td className="py-1.5 pr-4">{a.report_line}</td>
            <td className="py-1.5 pr-4">{a.is_cash ? "Yes" : ""}</td>
            <td className="py-1.5 pr-4">{a.is_postable ? "" : "Group only"}</td>
          </tr>
          {renderTree(a.id, depth + 1)}
        </Fragment>
      ));
  }

  if (!currentEntityId) return <p className="text-sm text-slate-500">Select a legal entity first.</p>;

  return (
    <div>
      <h1 className="mb-1 text-2xl font-semibold">Chart of Accounts</h1>
      <p className="mb-6 text-sm text-slate-500">{currentEntity?.name}</p>

      {canEdit && (
        <div className="mb-6 rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="mb-3 text-sm font-semibold">Import from CSV/Excel</h2>
          <p className="mb-2 text-xs text-slate-500">
            Columns: code, name, parent_code, account_type (asset/liability/equity/income/expense), report_line, is_cash
          </p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.xlsx,.xlsm"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) importMutation.mutate(file);
            }}
            className="text-sm"
          />
          {importMutation.isPending && <p className="mt-2 text-xs text-slate-500">Importing...</p>}
          {importResult && <p className="mt-2 text-xs text-slate-600">{importResult}</p>}

          <h2 className="mb-3 mt-6 text-sm font-semibold">Add account manually</h2>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              createMutation.mutate(form);
            }}
            className="grid grid-cols-2 gap-2 sm:grid-cols-6"
          >
            <input required placeholder="Code" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} className="rounded border border-slate-300 px-2 py-1 text-sm" />
            <input required placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="col-span-2 rounded border border-slate-300 px-2 py-1 text-sm" />
            <select value={form.account_type} onChange={(e) => setForm({ ...form, account_type: e.target.value as AccountType })} className="rounded border border-slate-300 px-2 py-1 text-sm">
              {ACCOUNT_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
            <input placeholder="Report line" value={form.report_line} onChange={(e) => setForm({ ...form, report_line: e.target.value })} className="rounded border border-slate-300 px-2 py-1 text-sm" />
            <button type="submit" className="rounded bg-slate-900 px-3 py-1 text-sm text-white">Add</button>
            <label className="col-span-2 flex items-center gap-1 text-xs text-slate-600">
              <input type="checkbox" checked={form.is_cash} onChange={(e) => setForm({ ...form, is_cash: e.target.checked })} />
              Cash/bank account
            </label>
          </form>
        </div>
      )}

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        {isLoading ? (
          <p className="text-sm text-slate-500">Loading...</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-300 text-xs uppercase text-slate-500">
                <th className="pb-2">Code</th>
                <th className="pb-2">Name</th>
                <th className="pb-2">Type</th>
                <th className="pb-2">Report Line</th>
                <th className="pb-2">Cash</th>
                <th className="pb-2">Postable</th>
              </tr>
            </thead>
            <tbody>{renderTree(null, 0)}</tbody>
          </table>
        )}
      </div>
    </div>
  );
}
