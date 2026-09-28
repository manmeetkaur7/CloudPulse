export type Project = { id: string; name: string; description: string | null; created_at: string };
export type Service = { id: string; project_id: string; name: string; environment: string; created_at: string };
export type Summary = { total_requests: number; average_latency_ms: number; error_rate: number; status: "healthy" | "degraded" };

const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    ...options,
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? "CloudPulse API request failed");
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>("/health"),
  listProjects: () => request<Project[]>("/api/projects"),
  createProject: (data: { name: string; description?: string }) => request<Project>("/api/projects", { method: "POST", body: JSON.stringify(data) }),
  listServices: (projectId: string) => request<Service[]>(`/api/projects/${projectId}/services`),
  createService: (projectId: string, data: { name: string; environment: string }) => request<Service>(`/api/projects/${projectId}/services`, { method: "POST", body: JSON.stringify(data) }),
  summary: (projectId: string) => request<Summary>(`/api/projects/${projectId}/summary`),
  sendTelemetry: (data: { project_id: string; service_id: string; event_type: "request" | "error"; duration_ms?: number; status_code?: number; message?: string }) => request("/api/telemetry", { method: "POST", body: JSON.stringify(data) }),
};
