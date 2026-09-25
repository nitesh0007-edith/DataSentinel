import type { DashboardState } from "@/types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(`Cannot reach the DataSentinel API at ${API_URL}. Is the backend running?`, 0);
  }
  const text = await res.text();
  if (!res.ok) {
    let detail = text;
    try {
      const body = JSON.parse(text);
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* plain-text error */
    }
    throw new ApiError(detail || `Request failed (${res.status})`, res.status);
  }
  const type = res.headers.get("content-type") ?? "";
  return (type.includes("application/json") ? JSON.parse(text) : text) as T;
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

export const api = {
  state: () => request<DashboardState>("/api/state"),
  reset: () => post("/api/demo/reset", {}),
  runPipeline: (setBaseline: boolean) => post("/api/pipeline/run", { set_baseline: setBaseline }),
  inject: (type: string) => post("/api/incidents/inject", { type }),
  detect: () => post("/api/incidents/detect"),
  investigate: (id: string) => post(`/api/incidents/${id}/investigate`),
  fix: (id: string) => post(`/api/incidents/${id}/fix`),
  reject: (id: string) => post(`/api/incidents/${id}/reject`),
  apply: (id: string) => post(`/api/incidents/${id}/apply`),
  validate: (id: string) => post(`/api/incidents/${id}/validate`),
  report: (id: string) => request<string>(`/api/incidents/${id}/report`),
};
