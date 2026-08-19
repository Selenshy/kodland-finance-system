"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiRequest, ApiError } from "@/lib/api";
import { useEntities } from "@/lib/entity-context";
import { useCurrencies } from "@/lib/hooks";

export default function EntitiesAdminPage() {
  const { entities, refetch } = useEntities();
  const { data: currencies = [] } = useCurrencies();
  const [name, setName] = useState("");
  const [country, setCountry] = useState("");
  const [functionalCurrency, setFunctionalCurrency] = useState("USD");
  const [copyFrom, setCopyFrom] = useState<number | "">("");
  const [error, setError] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: () =>
      apiRequest("/api/legal-entities", {
        method: "POST",
        body: {
          name,
          country,
          functional_currency: functionalCurrency,
          copy_coa_from_entity_id: copyFrom || null,
        },
      }),
    onSuccess: () => {
      refetch();
      setName("");
      setCountry("");
    },
    onError: (err) => setError(err instanceof ApiError ? String(err.detail) : "Failed to create"),
  });

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">Legal Entities</h1>

      <div className="mb-6 rounded-lg border border-slate-200 bg-white p-4">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-300 text-xs uppercase text-slate-500">
              <th className="pb-2">Name</th>
              <th className="pb-2">Country</th>
              <th className="pb-2">Functional Currency</th>
            </tr>
          </thead>
          <tbody>
            {entities.map((e) => (
              <tr key={e.id} className="border-b border-slate-100">
                <td className="py-1.5">{e.name}</td>
                <td className="py-1.5">{e.country}</td>
                <td className="py-1.5">{e.functional_currency}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold">New Legal Entity</h2>
        <form
          onSubmit={(e) => { e.preventDefault(); setError(null); createMutation.mutate(); }}
          className="grid grid-cols-2 gap-3 sm:grid-cols-4"
        >
          <input required placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
          <input placeholder="Country" value={country} onChange={(e) => setCountry(e.target.value)} className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
          <select value={functionalCurrency} onChange={(e) => setFunctionalCurrency(e.target.value)} className="rounded border border-slate-300 px-2 py-1.5 text-sm">
            {currencies.map((c) => (<option key={c.code} value={c.code}>{c.code} - {c.name}</option>))}
          </select>
          <select value={copyFrom} onChange={(e) => setCopyFrom(e.target.value ? Number(e.target.value) : "")} className="rounded border border-slate-300 px-2 py-1.5 text-sm">
            <option value="">Copy COA from... (optional)</option>
            {entities.map((e) => (<option key={e.id} value={e.id}>{e.name}</option>))}
          </select>
          <button type="submit" disabled={createMutation.isPending} className="col-span-2 rounded bg-slate-900 px-4 py-2 text-sm text-white sm:col-span-1">
            Create
          </button>
        </form>
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      </div>
    </div>
  );
}
