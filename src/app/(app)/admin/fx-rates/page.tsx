"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest, ApiError } from "@/lib/api";
import { FxRate } from "@/lib/types";
import { useCurrencies } from "@/lib/hooks";

export default function FxRatesAdminPage() {
  const queryClient = useQueryClient();
  const { data: currencies = [] } = useCurrencies();
  const { data: rates = [], isLoading } = useQuery({
    queryKey: ["fx-rates"],
    queryFn: () => apiRequest<FxRate[]>("/api/fx-rates"),
  });

  const [rateDate, setRateDate] = useState(new Date().toISOString().slice(0, 10));
  const [currencyFrom, setCurrencyFrom] = useState("EUR");
  const [currencyTo, setCurrencyTo] = useState("USD");
  const [rate, setRate] = useState("");
  const [error, setError] = useState<string | null>(null);

  const upsertMutation = useMutation({
    mutationFn: () =>
      apiRequest("/api/fx-rates", {
        method: "PUT",
        body: { rate_date: rateDate, currency_from: currencyFrom, currency_to: currencyTo, rate: Number(rate) },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fx-rates"] });
      setRate("");
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Failed to save rate"),
  });

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">FX Rates</h1>
      <p className="mb-4 text-sm text-slate-500">
        Rates are fetched automatically (CBR for RUB pairs, ECB via Frankfurter for others) on first use per date and
        cached here. Use this form to correct a rate manually when a provider doesn&apos;t cover a pair/date.
      </p>

      <div className="mb-6 rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold">Manual correction</h2>
        <form onSubmit={(e) => { e.preventDefault(); setError(null); upsertMutation.mutate(); }} className="flex flex-wrap items-end gap-3">
          <div>
            <label className="mb-1 block text-xs text-slate-500">Date</label>
            <input type="date" value={rateDate} onChange={(e) => setRateDate(e.target.value)} className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-500">From</label>
            <select value={currencyFrom} onChange={(e) => setCurrencyFrom(e.target.value)} className="rounded border border-slate-300 px-2 py-1.5 text-sm">
              {currencies.map((c) => (<option key={c.code} value={c.code}>{c.code}</option>))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-500">To</label>
            <select value={currencyTo} onChange={(e) => setCurrencyTo(e.target.value)} className="rounded border border-slate-300 px-2 py-1.5 text-sm">
              {currencies.map((c) => (<option key={c.code} value={c.code}>{c.code}</option>))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-500">Rate</label>
            <input type="number" step="0.000001" value={rate} onChange={(e) => setRate(e.target.value)} className="w-32 rounded border border-slate-300 px-2 py-1.5 text-sm" />
          </div>
          <button type="submit" disabled={upsertMutation.isPending} className="rounded bg-slate-900 px-4 py-2 text-sm text-white">Save</button>
        </form>
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        {isLoading ? (
          <p className="text-sm text-slate-500">Loading...</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-300 text-xs uppercase text-slate-500">
                <th className="pb-2">Date</th>
                <th className="pb-2">From</th>
                <th className="pb-2">To</th>
                <th className="pb-2 text-right">Rate</th>
                <th className="pb-2">Source</th>
              </tr>
            </thead>
            <tbody>
              {rates.map((r) => (
                <tr key={r.id} className="border-b border-slate-100">
                  <td className="py-1.5">{r.rate_date}</td>
                  <td className="py-1.5">{r.currency_from}</td>
                  <td className="py-1.5">{r.currency_to}</td>
                  <td className="py-1.5 text-right">{r.rate}</td>
                  <td className="py-1.5">{r.source}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
