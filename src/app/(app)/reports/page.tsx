"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiDownload, apiRequest } from "@/lib/api";
import { Report } from "@/lib/types";
import { useEntities } from "@/lib/entity-context";

type ReportType = "pl" | "cf" | "balance";

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function ReportsPage() {
  const { entities, currentEntityId } = useEntities();
  const [reportType, setReportType] = useState<ReportType>("pl");
  const [periodStart, setPeriodStart] = useState("2025-01-01");
  const [periodEnd, setPeriodEnd] = useState("2025-03-31");
  const [currency, setCurrency] = useState("USD");
  const [scope, setScope] = useState<"single" | "group">("single");
  const [exporting, setExporting] = useState(false);

  const selectedEntityIds = scope === "group" ? entities.map((e) => e.id) : currentEntityId ? [currentEntityId] : [];

  const { data: report, isLoading, error } = useQuery({
    queryKey: ["report", reportType, selectedEntityIds, periodStart, periodEnd, currency],
    queryFn: () =>
      apiRequest<Report>(`/api/reports/${reportType}`, {
        query: { legal_entity_ids: selectedEntityIds, period_start: periodStart, period_end: periodEnd, currency },
      }),
    enabled: selectedEntityIds.length > 0,
  });

  const doExport = async (format: "excel" | "pdf") => {
    setExporting(true);
    try {
      const blob = await apiDownload(`/api/reports/${reportType}/export/${format}`, {
        legal_entity_ids: selectedEntityIds,
        period_start: periodStart,
        period_end: periodEnd,
        currency,
      });
      downloadBlob(blob, `${reportType}_${periodStart}_${periodEnd}.${format === "excel" ? "xlsx" : "pdf"}`);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div>
      <h1 className="mb-4 text-2xl font-semibold">Reports</h1>

      <div className="mb-4 flex flex-wrap items-center gap-3 text-sm">
        <div className="flex gap-1 rounded bg-slate-100 p-1">
          {(["pl", "cf", "balance"] as ReportType[]).map((t) => (
            <button
              key={t}
              onClick={() => setReportType(t)}
              className={`rounded px-3 py-1 ${reportType === t ? "bg-white shadow-sm" : "text-slate-500"}`}
            >
              {t === "pl" ? "P&L" : t === "cf" ? "Cash Flow" : "Balance"}
            </button>
          ))}
        </div>

        <div className="flex gap-1 rounded bg-slate-100 p-1">
          <button onClick={() => setScope("single")} className={`rounded px-3 py-1 ${scope === "single" ? "bg-white shadow-sm" : "text-slate-500"}`}>Entity</button>
          <button onClick={() => setScope("group")} className={`rounded px-3 py-1 ${scope === "group" ? "bg-white shadow-sm" : "text-slate-500"}`}>Group (all)</button>
        </div>

        <label className="flex items-center gap-1">
          From <input type="date" value={periodStart} onChange={(e) => setPeriodStart(e.target.value)} className="rounded border border-slate-300 px-2 py-1" />
        </label>
        <label className="flex items-center gap-1">
          To <input type="date" value={periodEnd} onChange={(e) => setPeriodEnd(e.target.value)} className="rounded border border-slate-300 px-2 py-1" />
        </label>

        <select value={currency} onChange={(e) => setCurrency(e.target.value)} className="rounded border border-slate-300 px-2 py-1">
          <option value="USD">USD</option>
          {scope === "single" && entities.find((e) => e.id === currentEntityId) && (
            <option value={entities.find((e) => e.id === currentEntityId)!.functional_currency}>
              {entities.find((e) => e.id === currentEntityId)!.functional_currency} (local)
            </option>
          )}
        </select>

        <div className="ml-auto flex gap-2">
          <button disabled={!report || exporting} onClick={() => doExport("excel")} className="rounded border border-slate-300 px-3 py-1.5 text-xs disabled:opacity-50">
            Export Excel
          </button>
          <button disabled={!report || exporting} onClick={() => doExport("pdf")} className="rounded border border-slate-300 px-3 py-1.5 text-xs disabled:opacity-50">
            Export PDF
          </button>
        </div>
      </div>

      {isLoading && <p className="text-sm text-slate-500">Loading...</p>}
      {error && <p className="text-sm text-red-600">Failed to load report.</p>}

      {report && (
        <div className="rounded-lg border border-slate-200 bg-white p-6">
          {report.check_ok !== null && (
            <p className={`mb-4 text-sm ${report.check_ok ? "text-green-700" : "text-red-600"}`}>
              Assets = Liabilities + Equity check: {report.check_ok ? "OK" : "MISMATCH"}
            </p>
          )}
          {report.sections.map((section) => (
            <div key={section.title} className="mb-6">
              <h3 className="mb-2 text-sm font-semibold">{section.title}</h3>
              <table className="w-full text-left text-sm">
                <tbody>
                  {section.lines.map((line) => (
                    <tr key={line.code} className={`border-b border-slate-100 ${line.is_subtotal ? "font-semibold" : ""}`}>
                      <td className="py-1.5">{line.label}</td>
                      <td className="py-1.5 text-right">{line.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                    </tr>
                  ))}
                  <tr className="font-semibold">
                    <td className="py-1.5">Total</td>
                    <td className="py-1.5 text-right">{section.total.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
