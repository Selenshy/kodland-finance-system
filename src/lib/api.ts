const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

function stringifyDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (detail === null || detail === undefined) return "Request failed";
  try {
    return JSON.stringify(detail);
  } catch {
    return String(detail);
  }
}

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(stringifyDetail(detail));
    this.status = status;
    this.detail = detail;
  }
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("access_token");
}

export function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem("access_token", token);
  else window.localStorage.removeItem("access_token");
}

type RequestOptions = {
  method?: string;
  body?: unknown;
  isForm?: boolean;
  query?: Record<string, string | number | boolean | undefined | null | (string | number)[]>;
};

function buildQuery(query?: RequestOptions["query"]): string {
  if (!query) return "";
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null) continue;
    if (Array.isArray(value)) {
      for (const v of value) params.append(key, String(v));
    } else {
      params.append(key, String(value));
    }
  }
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let body: BodyInit | undefined;
  if (options.body !== undefined) {
    if (options.isForm) {
      body = options.body as FormData;
    } else {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(options.body);
    }
  }

  const res = await fetch(`${API_URL}${path}${buildQuery(options.query)}`, {
    method: options.method || "GET",
    headers,
    body,
  });

  if (res.status === 204) return undefined as T;

  // Error bodies aren't always JSON: a crash before FastAPI's handlers run
  // (e.g. a bad DATABASE_URL) surfaces as Starlette's plain-text 500, and
  // infra-level failures (bad gateway, function crash) can come back as
  // HTML. Read as text and only parse as JSON when it looks like JSON, so
  // a non-JSON error still renders as readable text instead of "[object
  // Blob]"/"[object Object]".
  const contentType = res.headers.get("content-type") || "";
  const rawText = await res.text();
  let data: unknown = rawText;
  if (contentType.includes("application/json") && rawText) {
    try {
      data = JSON.parse(rawText);
    } catch {
      data = rawText;
    }
  }

  if (!res.ok) {
    const detail =
      data && typeof data === "object" && "detail" in (data as Record<string, unknown>)
        ? (data as { detail?: unknown }).detail
        : data || res.statusText || `Request failed with status ${res.status}`;
    throw new ApiError(res.status, detail);
  }
  return data as T;
}

export async function apiDownload(path: string, query?: RequestOptions["query"]): Promise<Blob> {
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_URL}${path}${buildQuery(query)}`, { headers });
  if (!res.ok) {
    throw new ApiError(res.status, await res.text());
  }
  return res.blob();
}
