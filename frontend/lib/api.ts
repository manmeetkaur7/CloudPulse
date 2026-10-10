export type Project = { id: string; name: string; description: string | null; created_at: string };
export type Service = { id: string; project_id: string; name: string; environment: string; created_at: string };
export type Summary = { total_requests: number; average_latency_ms: number; error_rate: number; status: "healthy" | "degraded" };
export type MetricsTimeRange = "15m" | "1h" | "24h" | "7d";
export type MetricsBucket = { timestamp: string; request_count: number; error_count: number; error_rate: number; average_latency_ms: number; p95_latency_ms: number };
export type ProjectMetrics = { time_range: MetricsTimeRange; bucket_width_seconds: number; buckets: MetricsBucket[] };
export type TelemetryEvent = { id: string; project_id: string; service_id: string; event_type: "request" | "error"; timestamp: string; duration_ms: number | null; status_code: number | null; message: string | null; trace_id: string | null; span_id: string | null; http_method: string | null; http_route: string | null };
export type TelemetryInput = { project_id: string; service_id: string; event_type: "request" | "error"; timestamp?: string; duration_ms?: number; status_code?: number; message?: string; trace_id?: string; span_id?: string; http_method?: string; http_route?: string };

const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function telemetryWebSocketUrl(projectId: string): string {
  const url = new URL(baseUrl);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = `/ws/projects/${projectId}/telemetry`;
  return url.toString();
}

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
  metrics: (projectId: string, timeRange: MetricsTimeRange, signal?: AbortSignal) => request<ProjectMetrics>(`/api/v1/projects/${projectId}/metrics?time_range=${timeRange}`, { signal }),
  listTelemetry: (projectId: string) => request<TelemetryEvent[]>(`/api/projects/${projectId}/telemetry?limit=10`),
  sendTelemetry: (data: TelemetryInput) => request<TelemetryEvent>("/api/v1/telemetry/events", { method: "POST", body: JSON.stringify(data) }),
};
