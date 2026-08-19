"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiRequest, ApiError } from "@/lib/api";
import { useAccounts, useCostCenters, useCounterparties, useCurrencies, useProjects } from "@/lib/hooks";
import { EntryDirection } from "@/lib/types";

type LineForm = {
  account_id: number | "";
  direction: EntryDirection;
  transaction_currency: string;
  transaction_amount: string;
  cost_center_id: number | "";
  counterparty_id: number | "";
  project_id: number | "";
  memo: string;
};

const emptyLine = (direction: EntryDirection, currency: string): LineForm => ({
  account_id: "",
  direction,
  transaction_currency: currency,
  transaction_amount: "",
  cost_center_id: "",
  counterparty_id: "",
  project_id: "",
  memo: "",
});

export function JournalEntryModal({
  entityId,
  functionalCurrency,
  onClose,
}: {
  entityId: number;
  functionalCurrency: string;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const { data: accounts = [] } = useAccounts(entityId);
  const { data: costCenters = [] } = useCostCenters(entityId);
  const { data: counterparties = [] } = useCounterparties(entityId);
  const { data: projects = [] } = useProjects(entityId);
  const { data: currencies = [] } = useCurrencies();

  const [entryDate, setEntryDate] = useState(new Date().toISOString().slice(0, 10));
  const [description, setDescription] = useState("");
  const [lines, setLines] = useState<LineForm[]>([
    emptyLine("debit", functionalCurrency),
    emptyLine("credit", functionalCurrency),
  ]);
  const [error, setError] = useState<string | null>(null);

  const postableAccounts = accounts.filter((a) => a.is_postable);

  const mutation = useMutation({
    mutationFn: () =>
      apiRequest(`/api/legal-entities/${entityId}/journal-entries`, {
        method: "POST",
        body: {
          legal_entity_id: entityId,
          entry_date: entryDate,
          description,
          lines: lines.map((l) => ({
            account_id: Number(l.account_id),
            direction: l.direction,
            transaction_currency: l.transaction_currency,
            transaction_amount: Number(l.transaction_amount),
            cost_center_id: l.cost_center_id || null,
            counterparty_id: l.counterparty_id || null,
            project_id: l.project_id || null,
            memo: l.memo,
          })),
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["journal-entries", entityId] });
      onClose();
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Failed to save entry"),
  });

  const updateLine = (i: number, patch: Partial<LineForm>) => {
    setLines((prev) => prev.map((l, idx) => (idx === i ? { ...l, ...patch } : l)));
  };

  const debitTotal = lines.filter((l) => l.direction === "debit").reduce((s, l) => s + (Number(l.transaction_amount) || 0), 0);
  const creditTotal = lines.filter((l) => l.direction === "credit").reduce((s, l) => s + (Number(l.transaction_amount) || 0), 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="max-h-[90vh] w-full max-w-3xl overflow-auto rounded-lg bg-white p-6 shadow-xl">
        <h2 className="mb-4 text-lg font-semibold">New Journal Entry</h2>

        <div className="mb-4 grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Date</label>
            <input type="date" value={entryDate} onChange={(e) => setEntryDate(e.target.value)} className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm" />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Description</label>
            <input value={description} onChange={(e) => setDescription(e.target.value)} className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm" />
          </div>
        </div>

        <table className="mb-3 w-full text-left text-xs">
          <thead>
            <tr className="text-slate-500">
              <th className="pb-1">Dir</th>
              <th className="pb-1">Account</th>
              <th className="pb-1">Currency</th>
              <th className="pb-1">Amount</th>
              <th className="pb-1">Cost Center</th>
              <th className="pb-1">Counterparty</th>
              <th className="pb-1">Project</th>
              <th className="pb-1"></th>
            </tr>
          </thead>
          <tbody>
            {lines.map((line, i) => (
              <tr key={i}>
                <td className="pr-1 py-1">
                  <select value={line.direction} onChange={(e) => updateLine(i, { direction: e.target.value as EntryDirection })} className="rounded border border-slate-300 px-1 py-1 text-xs">
                    <option value="debit">Debit</option>
                    <option value="credit">Credit</option>
                  </select>
                </td>
                <td className="pr-1 py-1">
                  <select value={line.account_id} onChange={(e) => updateLine(i, { account_id: Number(e.target.value) })} className="rounded border border-slate-300 px-1 py-1 text-xs">
                    <option value="">Select...</option>
                    {postableAccounts.map((a) => (
                      <option key={a.id} value={a.id}>{a.code} {a.name}</option>
                    ))}
                  </select>
                </td>
                <td className="pr-1 py-1">
                  <select value={line.transaction_currency} onChange={(e) => updateLine(i, { transaction_currency: e.target.value })} className="rounded border border-slate-300 px-1 py-1 text-xs">
                    {currencies.map((c) => (
                      <option key={c.code} value={c.code}>{c.code}</option>
                    ))}
                  </select>
                </td>
                <td className="pr-1 py-1">
                  <input type="number" step="0.01" value={line.transaction_amount} onChange={(e) => updateLine(i, { transaction_amount: e.target.value })} className="w-24 rounded border border-slate-300 px-1 py-1 text-xs" />
                </td>
                <td className="pr-1 py-1">
                  <select value={line.cost_center_id} onChange={(e) => updateLine(i, { cost_center_id: e.target.value ? Number(e.target.value) : "" })} className="rounded border border-slate-300 px-1 py-1 text-xs">
                    <option value="">-</option>
                    {costCenters.map((c) => (<option key={c.id} value={c.id}>{c.name}</option>))}
                  </select>
                </td>
                <td className="pr-1 py-1">
                  <select value={line.counterparty_id} onChange={(e) => updateLine(i, { counterparty_id: e.target.value ? Number(e.target.value) : "" })} className="rounded border border-slate-300 px-1 py-1 text-xs">
                    <option value="">-</option>
                    {counterparties.map((c) => (<option key={c.id} value={c.id}>{c.name}</option>))}
                  </select>
                </td>
                <td className="pr-1 py-1">
                  <select value={line.project_id} onChange={(e) => updateLine(i, { project_id: e.target.value ? Number(e.target.value) : "" })} className="rounded border border-slate-300 px-1 py-1 text-xs">
                    <option value="">-</option>
                    {projects.map((c) => (<option key={c.id} value={c.id}>{c.name}</option>))}
                  </select>
                </td>
                <td className="py-1">
                  {lines.length > 2 && (
                    <button onClick={() => setLines((prev) => prev.filter((_, idx) => idx !== i))} className="text-red-500">✕</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <button
          onClick={() => setLines((prev) => [...prev, emptyLine("debit", functionalCurrency)])}
          className="mb-4 text-xs text-slate-600 underline"
        >
          + Add line
        </button>

        <div className="mb-4 flex gap-6 text-xs">
          <span>Debit total: <strong>{debitTotal.toFixed(2)}</strong></span>
          <span>Credit total: <strong>{creditTotal.toFixed(2)}</strong></span>
          {Math.abs(debitTotal - creditTotal) > 0.01 && <span className="text-red-600">Not balanced yet</span>}
        </div>

        {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="rounded border border-slate-300 px-4 py-1.5 text-sm">Cancel</button>
          <button
            onClick={() => {
              setError(null);
              mutation.mutate();
            }}
            disabled={mutation.isPending}
            className="rounded bg-slate-900 px-4 py-1.5 text-sm text-white disabled:opacity-50"
          >
            {mutation.isPending ? "Saving..." : "Save Entry"}
          </button>
        </div>
      </div>
    </div>
  );
}
