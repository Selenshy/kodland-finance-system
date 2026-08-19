"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest, ApiError } from "@/lib/api";
import { OpeningBalance } from "@/lib/types";
import { useEntities } from "@/lib/entity-context";
import { useAuth } from "@/lib/auth-context";
import { useAccounts } from "@/lib/hooks";

export default function OpeningBalancesPage() {
  const { currentEntityId, currentEntity } = useEntities();
  const { isAtLeast } = useAuth();
  const queryClient = useQueryClient();
  const canEdit = isAtLeast("accountant");

  const { data: accounts = [] } = useAccounts(currentEntityId);
  const { data: balances = [], isLoading } = useQuery({
    queryKey: ["opening-balances", currentEntityId],
    queryFn: () => apiRequest<OpeningBalance[]>(`/api/legal-entities/${currentEntityId}/opening-balances`),
    enabled: !!currentEntityId,
  });

  const [accountId, setAccountId] = useState<number | "">("");
  const [asOfDate, setAsOfDate] = useState("2025-01-01");
  const [localAmount, setLocalAmount] = useState("");
  const [usdAmount, setUsdAmount] = useState("");
  const [error, setError] = useState<string | null>(null);

  const postableAccounts = accounts.filter((a) => a.is_postable);
  const accountById = new Map(accounts.map((a) => [a.id, a]));

  const upsertMutation = useMutation({
    mutationFn: () =>
      apiRequest(`/api/legal-entities/${currentEntityId}/opening-balances`, {
        method: "PUT",
        body: { account_id: accountId, as_of_date: asOfDate, local_currency_amount: Number(localAmount), usd_amount: Number(usdAmount) },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["opening-balances", currentEntityId] });
      setAccountId(""); setLocalAmount(""); setUsdAmount("");
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Failed to save"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => apiRequest(`/api/legal-entities/${currentEntityId}/opening-balances/${id}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["opening-balances", currentEntityId] }),
  });

  const totalLocal = balances.reduce((s, b) => s + b.local_currency_amount, 0);

  if (!currentEntityId) return <p className="text-sm text-slate-500">Select a legal entity first.</p>;

  return (
    <div>
      <h1 className="mb-1 text-2xl font-semibold">Opening Balances</h1>
      <p className="mb-6 text-sm text-slate-500">{currentEntity?.name} — starting point for ledger-based accounting</p>

      <div className="mb-6 rounded-lg border border-slate-200 bg-white p-4">
        <p className="mb-3 text-xs text-slate-500">
          Amounts use a debit-positive convention: positive for asset/expense accounts, negative for
          liability/equity/income accounts. A balanced trial balance sums to zero.
        </p>
        {isLoading ? (
          <p className="text-sm text-slate-500">Loading...</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-300 text-xs uppercase text-slate-500">
                <th className="pb-2">As of</th>
                <th className="pb-2">Account</th>
                <th className="pb-2 text-right">Local</th>
                <th className="pb-2 text-right">USD</th>
                {canEdit && <th className="pb-2"></th>}
              </tr>
            </thead>
            <tbody>
              {balances.map((b) => (
                <tr key={b.id} className="border-b border-slate-100">
                  <td className="py-1.5">{b.as_of_date}</td>
                  <td className="py-1.5">{accountById.get(b.account_id)?.code} {accountById.get(b.account_id)?.name}</td>
                  <td className="py-1.5 text-right">{b.local_currency_amount.toLocaleString()}</td>
                  <td className="py-1.5 text-right">{b.usd_amount.toLocaleString()}</td>
                  {canEdit && (
                    <td className="py-1.5">
                      <button onClick={() => deleteMutation.mutate(b.id)} className="text-xs text-red-500">Delete</button>
                    </td>
                  )}
                </tr>
              ))}
              <tr className="font-semibold">
                <td className="py-1.5" colSpan={2}>Sum (should be 0 if balanced)</td>
                <td className="py-1.5 text-right">{totalLocal.toLocaleString()}</td>
                <td></td>
                {canEdit && <td></td>}
              </tr>
            </tbody>
          </table>
        )}
      </div>

      {canEdit && (
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="mb-3 text-sm font-semibold">Set / update opening balance</h2>
          <form
            onSubmit={(e) => { e.preventDefault(); setError(null); upsertMutation.mutate(); }}
            className="grid grid-cols-2 gap-3 sm:grid-cols-5"
          >
            <select required value={accountId} onChange={(e) => setAccountId(Number(e.target.value))} className="rounded border border-slate-300 px-2 py-1.5 text-sm">
              <option value="">Account...</option>
              {postableAccounts.map((a) => (<option key={a.id} value={a.id}>{a.code} {a.name}</option>))}
            </select>
            <input type="date" required value={asOfDate} onChange={(e) => setAsOfDate(e.target.value)} className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
            <input type="number" step="0.01" required placeholder="Local amount" value={localAmount} onChange={(e) => setLocalAmount(e.target.value)} className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
            <input type="number" step="0.01" required placeholder="USD amount" value={usdAmount} onChange={(e) => setUsdAmount(e.target.value)} className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
            <button type="submit" disabled={upsertMutation.isPending} className="rounded bg-slate-900 px-4 py-1.5 text-sm text-white">Save</button>
          </form>
          {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
        </div>
      )}
    </div>
  );
}
