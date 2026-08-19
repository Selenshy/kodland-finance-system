"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest, ApiError } from "@/lib/api";
import { useEntities } from "@/lib/entity-context";
import { ImportCommitResult, ImportMappingTemplate, ImportUploadResult, ImportValidateResult } from "@/lib/types";

const REQUIRED_FIELDS = ["entry_date", "debit_account_code", "credit_account_code", "amount"];
const OPTIONAL_FIELDS = ["description", "currency", "cost_center", "counterparty", "project"];
const ALL_FIELDS = [...REQUIRED_FIELDS, ...OPTIONAL_FIELDS];

type Step = "upload" | "map" | "validate" | "commit";

export default function ImportPage() {
  const { currentEntityId, currentEntity } = useEntities();
  const queryClient = useQueryClient();
  const [step, setStep] = useState<Step>("upload");
  const [file, setFile] = useState<File | null>(null);
  const [upload, setUpload] = useState<ImportUploadResult | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [validation, setValidation] = useState<ImportValidateResult | null>(null);
  const [commitResult, setCommitResult] = useState<ImportCommitResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [templateName, setTemplateName] = useState("");

  const { data: templates = [] } = useQuery({
    queryKey: ["mapping-templates", currentEntityId],
    queryFn: () => apiRequest<ImportMappingTemplate[]>(`/api/legal-entities/${currentEntityId}/imports/mapping-templates`),
    enabled: !!currentEntityId,
  });

  const uploadMutation = useMutation({
    mutationFn: async () => {
      const fd = new FormData();
      fd.append("file", file!);
      return apiRequest<ImportUploadResult>(`/api/legal-entities/${currentEntityId}/imports/upload`, { method: "POST", body: fd, isForm: true });
    },
    onSuccess: (res) => {
      setUpload(res);
      setStep("map");
    },
    onError: (err) => setError(err instanceof ApiError ? String(err.detail) : "Upload failed"),
  });

  const validateMutation = useMutation({
    mutationFn: () =>
      apiRequest<ImportValidateResult>(`/api/legal-entities/${currentEntityId}/imports/validate`, {
        method: "POST",
        body: { upload_token: upload!.upload_token, legal_entity_id: currentEntityId, column_mapping: mapping },
      }),
    onSuccess: (res) => {
      setValidation(res);
      setStep("validate");
    },
    onError: (err) => setError(err instanceof ApiError ? String(err.detail) : "Validation failed"),
  });

  const commitMutation = useMutation({
    mutationFn: () =>
      apiRequest<ImportCommitResult>(`/api/legal-entities/${currentEntityId}/imports/commit`, {
        method: "POST",
        body: { upload_token: upload!.upload_token, legal_entity_id: currentEntityId, column_mapping: mapping, file_name: file?.name || "import" },
      }),
    onSuccess: (res) => {
      setCommitResult(res);
      setStep("commit");
      queryClient.invalidateQueries({ queryKey: ["journal-entries", currentEntityId] });
    },
    onError: (err) => setError(err instanceof ApiError ? String(err.detail) : "Commit failed"),
  });

  const saveTemplateMutation = useMutation({
    mutationFn: () =>
      apiRequest(`/api/legal-entities/${currentEntityId}/imports/mapping-templates`, {
        method: "POST",
        body: { legal_entity_id: currentEntityId, name: templateName, column_mapping: mapping },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mapping-templates", currentEntityId] });
      setTemplateName("");
    },
  });

  const reset = () => {
    setStep("upload");
    setFile(null);
    setUpload(null);
    setMapping({});
    setValidation(null);
    setCommitResult(null);
    setError(null);
  };

  if (!currentEntityId) return <p className="text-sm text-slate-500">Select a legal entity first.</p>;

  return (
    <div>
      <h1 className="mb-1 text-2xl font-semibold">Import Wizard</h1>
      <p className="mb-6 text-sm text-slate-500">{currentEntity?.name}</p>

      <div className="mb-6 flex gap-2 text-xs">
        {(["upload", "map", "validate", "commit"] as Step[]).map((s, i) => (
          <div key={s} className={`rounded px-3 py-1 ${step === s ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-500"}`}>
            {i + 1}. {s}
          </div>
        ))}
      </div>

      {error && <p className="mb-4 rounded bg-red-50 p-3 text-sm text-red-600">{error}</p>}

      {step === "upload" && (
        <div className="rounded-lg border border-slate-200 bg-white p-6">
          <p className="mb-3 text-sm text-slate-600">Upload a CSV or Excel register of transactions.</p>
          <input type="file" accept=".csv,.xlsx,.xlsm" onChange={(e) => setFile(e.target.files?.[0] || null)} className="mb-4 text-sm" />
          <button
            disabled={!file || uploadMutation.isPending}
            onClick={() => { setError(null); uploadMutation.mutate(); }}
            className="rounded bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50"
          >
            {uploadMutation.isPending ? "Uploading..." : "Upload"}
          </button>
        </div>
      )}

      {step === "map" && upload && (
        <div className="rounded-lg border border-slate-200 bg-white p-6">
          <p className="mb-3 text-sm text-slate-600">{upload.total_rows} rows detected. Map each field to a column, or a fixed value using "const:VALUE".</p>

          {templates.length > 0 && (
            <div className="mb-4">
              <label className="mb-1 block text-xs font-medium text-slate-500">Load saved mapping template</label>
              <select
                className="rounded border border-slate-300 px-2 py-1.5 text-sm"
                onChange={(e) => {
                  const t = templates.find((t) => t.id === Number(e.target.value));
                  if (t) setMapping(t.column_mapping);
                }}
              >
                <option value="">Select template...</option>
                {templates.map((t) => (<option key={t.id} value={t.id}>{t.name}</option>))}
              </select>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            {ALL_FIELDS.map((field) => (
              <div key={field}>
                <label className="mb-1 block text-xs font-medium text-slate-500">
                  {field} {REQUIRED_FIELDS.includes(field) && <span className="text-red-500">*</span>}
                </label>
                <select
                  value={mapping[field] || ""}
                  onChange={(e) => setMapping({ ...mapping, [field]: e.target.value })}
                  className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
                >
                  <option value="">-- not mapped --</option>
                  {upload.columns.map((c) => (<option key={c} value={c}>{c}</option>))}
                </select>
              </div>
            ))}
          </div>

          <div className="mt-4 overflow-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="text-slate-500">
                  {upload.columns.map((c) => (<th key={c} className="pb-1 pr-3">{c}</th>))}
                </tr>
              </thead>
              <tbody>
                {upload.preview_rows.slice(0, 5).map((row, i) => (
                  <tr key={i}>
                    {upload.columns.map((c) => (<td key={c} className="pr-3 py-1">{String(row[c] ?? "")}</td>))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 flex items-center gap-2">
            <input placeholder="Save mapping as template..." value={templateName} onChange={(e) => setTemplateName(e.target.value)} className="rounded border border-slate-300 px-2 py-1.5 text-sm" />
            <button disabled={!templateName || saveTemplateMutation.isPending} onClick={() => saveTemplateMutation.mutate()} className="rounded border border-slate-300 px-3 py-1.5 text-sm disabled:opacity-50">
              Save template
            </button>
          </div>

          <div className="mt-6 flex justify-end gap-2">
            <button onClick={reset} className="rounded border border-slate-300 px-4 py-2 text-sm">Start over</button>
            <button
              disabled={validateMutation.isPending}
              onClick={() => { setError(null); validateMutation.mutate(); }}
              className="rounded bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50"
            >
              {validateMutation.isPending ? "Validating..." : "Validate"}
            </button>
          </div>
        </div>
      )}

      {step === "validate" && validation && (
        <div className="rounded-lg border border-slate-200 bg-white p-6">
          <p className="mb-2 text-sm">
            <span className="font-medium text-green-700">{validation.valid_rows} valid</span>,{" "}
            <span className="font-medium text-red-600">{validation.invalid_rows} invalid</span> rows.
          </p>
          {validation.errors.length > 0 && (
            <ul className="mb-4 max-h-48 overflow-auto rounded border border-red-200 bg-red-50 p-3 text-xs text-red-700">
              {validation.errors.map((e, i) => (
                <li key={i}>Row {e.row_number}: {e.message}</li>
              ))}
            </ul>
          )}
          <div className="flex justify-end gap-2">
            <button onClick={() => setStep("map")} className="rounded border border-slate-300 px-4 py-2 text-sm">Back to mapping</button>
            <button
              disabled={!validation.can_commit || commitMutation.isPending}
              onClick={() => { setError(null); commitMutation.mutate(); }}
              className="rounded bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50"
            >
              {commitMutation.isPending ? "Committing..." : `Commit ${validation.valid_rows} rows`}
            </button>
          </div>
        </div>
      )}

      {step === "commit" && commitResult && (
        <div className="rounded-lg border border-slate-200 bg-white p-6">
          <p className="mb-4 text-sm text-green-700">
            Import complete: {commitResult.entries_created} journal entries ({commitResult.lines_created} lines) created.
            {commitResult.error_count > 0 && ` ${commitResult.error_count} rows skipped due to errors.`}
          </p>
          <button onClick={reset} className="rounded bg-slate-900 px-4 py-2 text-sm text-white">Import another file</button>
        </div>
      )}
    </div>
  );
}
