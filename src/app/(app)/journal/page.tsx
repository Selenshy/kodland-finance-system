"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import { JournalEntry } from "@/lib/types";
import { useEntities } from "@/lib/entity-context";
import { useAuth } from "@/lib/auth-context";
import { useAccounts, useCostCenters, useCounterparties, useProjects } from "@/lib/hooks";
import { JournalEntryModal } from "@/components/JournalEntryModal";

export default function JournalPage() {
  const { currentEntityId, currentEntity } = useEntities();
  const { isAtLeast } = useAuth();
  const queryClient = useQueryClient();

  const [dateFrom, setDateFrom] = useState("2025-01-01");
  const [dateTo, setDateTo] = useState("2025-12-31");
  const [showModal, setShowModal] = useState(false);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [bulkField, setBulkField] = useState<"counterparty_id" | "cost_center_id" | "project_id" | "account_id">("counterparty_id");
  const [bulkValue, setBulkValue] = useState<number | "">("");

  const canEdit = isAtLeast("accountant");

  const { data: entries = [], isLoading } = useQuery({
    queryKey: ["journal-entries", currentEntityId, dateFrom, dateTo],
    queryFn: () =>
      apiRequest<JournalEntry[]>(`/api/legal-entities/${currentEntityId}/journal-entries`, {
        query: { date_from: dateFrom, date_to: dateTo, limit: 500 },
      }),
    enabled: !!currentEntityId,
  });

  const { data: accounts = [] } = useAccounts(currentEntityId);
  const { data: costCenters = [] } = useCostCenters(currentEntityId);
  const { data: counterparties = [] } = useCounterparties(currentEntityId);
  const { data: projects = [] } = useProjects(currentEntityId);

  const accountById = useMemo(() => new Map(accounts.map((a) => [a.id, a])), [accounts]);

  const deleteMutation = useMutation({
    mutationFn: (entryId: number) => apiRequest(`/api/legal-entities/${currentEntityId}/journal-entries/${entryId}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["journal-entries", currentEntityId] }),
  });

  const bulkEditMutation = useMutation({
    mutationFn: () =>
      apiRequest(`/api/legal-entities/${currentEntityId}/journal-entries/bulk-edit`, {
        method: "POST",
        body: {
          entry_ids: Array.from(selected),
          [`set_${bulkField}`]: bulkValue,
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["journal-entries", currentEntityId] });
      setSelected(new Set());
      setBulkValue("");
    },
  });

  const toggle = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const bulkOptions =
    bulkField === "counterparty_id" ? counterparties : bulkField === "cost_center_id" ? costCenters : bulkField === "project_id" ? projects : accounts;

  if (!currentEntityId) return <p className="text-sm text-slate-500">Select a legal entity first.</p>;

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Journal Entries</h1>
          <p className="text-sm text-slate-500">{currentEntity?.name}</p>
        </div>
        {canEdit && (
          <button onClick={() => setShowModal(true)} className="rounded bg-slate-900 px-4 py-2 text-sm text-white">
            + New Entry
          </button>
        )}
      </div>

      <div className="mb-4 flex items-center gap-3 text-sm">
        <label className="flex items-center gap-1">
          From <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="rounded border border-slate-300 px-2 py-1" />
        </label>
        <label className="flex items-center gap-1">
          To <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="rounded border border-slate-300 px-2 py-1" />
        </label>
      </div>

      {canEdit && selected.size > 0 && (
        <div className="mb-4 flex items-center gap-2 rounded border border-amber-300 bg-amber-50 p-3 text-sm">
          <span>{selected.size} entries selected. Bulk set:</span>
          <select value={bulkField} onChange={(e) => { setBulkField(e.target.value as typeof bulkField); setBulkValue(""); }} className="rounded border border-slate-300 px-2 py-1">
            <option value="counterparty_id">Counterparty</option>
            <option value="cost_center_id">Cost Center</option>
            <option value="project_id">Project</option>
            <option value="account_id">Account</option>
          </select>
          <select value={bulkValue} onChange={(e) => setBulkValue(Number(e.target.value))} className="rounded border border-slate-300 px-2 py-1">
            <option value="">Select value...</option>
            {bulkOptions.map((o) => (
              <option key={o.id} value={o.id}>
                {"code" in o ? `${o.code} ${o.name}` : o.name}
              </option>
            ))}
          </select>
          <button disabled={!bulkValue || bulkEditMutation.isPending} onClick={() => bulkEditMutation.mutate()} className="rounded bg-slate-900 px-3 py-1 text-white disabled:opacity-50">
            Apply
          </button>
        </div>
      )}

      <div className="overflow-auto rounded-lg border border-slate-200 bg-white">
        {isLoading ? (
          <p className="p-4 text-sm text-slate-500">Loading...</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-300 text-xs uppercase text-slate-500">
                {canEdit && <th className="p-2"></th>}
                <th className="p-2">Date</th>
                <th className="p-2">Description</th>
                <th className="p-2">Account</th>
                <th className="p-2">Dir</th>
                <th className="p-2 text-right">Txn Amount</th>
                <th className="p-2">Ccy</th>
                <th className="p-2 text-right">Local</th>
                <th className="p-2 text-right">USD</th>
                {canEdit && <th className="p-2"></th>}
              </tr>
            </thead>
            <tbody>
              {entries.flatMap((entry) =>
                entry.lines.map((line, i) => (
                  <tr key={line.id} className="border-b border-slate-100">
                    {canEdit && (
                      <td className="p-2">
                        {i === 0 && <input type="checkbox" checked={selected.has(entry.id)} onChange={() => toggle(entry.id)} />}
                      </td>
                    )}
                    <td className="p-2">{i === 0 ? entry.entry_date : ""}</td>
                    <td className="p-2">{i === 0 ? entry.description : ""}</td>
                    <td className="p-2">{accountById.get(line.account_id)?.code} {accountById.get(line.account_id)?.name}</td>
                    <td className="p-2 capitalize">{line.direction}</td>
                    <td className="p-2 text-right">{line.transaction_amount.toLocaleString()}</td>
                    <td className="p-2">{line.transaction_currency}</td>
                    <td className="p-2 text-right">{line.local_currency_amount.toLocaleString()}</td>
                    <td className="p-2 text-right">{line.usd_amount.toLocaleString()}</td>
                    {canEdit && (
                      <td className="p-2">
                        {i === 0 && (
                          <button onClick={() => { if (confirm("Delete this entry?")) deleteMutation.mutate(entry.id); }} className="text-xs text-red-500">
                            Delete
                          </button>
                        )}
                      </td>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </div>

      {showModal && currentEntity && (
        <JournalEntryModal entityId={currentEntity.id} functionalCurrency={currentEntity.functional_currency} onClose={() => setShowModal(false)} />
      )}
    </div>
  );
}
