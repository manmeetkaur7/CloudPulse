"use client";

import { FormEvent, useEffect, useState } from "react";
import { MetricsCharts } from "./metrics-charts";
import { api, MetricsTimeRange, Project, ProjectMetrics, Service, Summary, TelemetryEvent, telemetryWebSocketUrl } from "../lib/api";

type ConnectionStatus = "checking" | "connected" | "unavailable";
type LiveStatus = "connecting" | "live" | "reconnecting" | "offline";

export function Dashboard() {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("checking");
  const [liveStatus, setLiveStatus] = useState<LiveStatus>("offline");
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [services, setServices] = useState<Service[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [recentTelemetry, setRecentTelemetry] = useState<TelemetryEvent[]>([]);
  const [metrics, setMetrics] = useState<ProjectMetrics | null>(null);
  const [metricsRange, setMetricsRange] = useState<MetricsTimeRange>("1h");
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [metricsError, setMetricsError] = useState<string | null>(null);
  const [metricsRefreshKey, setMetricsRefreshKey] = useState(0);
  const [projectName, setProjectName] = useState("");
  const [projectDescription, setProjectDescription] = useState("");
  const [serviceName, setServiceName] = useState("");
  const [environment, setEnvironment] = useState("development");
  const [notice, setNotice] = useState<string>("");

  const selectedProject = projects.find((project) => project.id === selectedProjectId);

  async function refreshProjects() {
    const items = await api.listProjects();
    setProjects(items);
    setSelectedProjectId((current) => current || items[0]?.id || "");
  }

  async function refreshProjectDetails(projectId: string) {
    const [serviceItems, projectSummary, events] = await Promise.all([api.listServices(projectId), api.summary(projectId), api.listTelemetry(projectId)]);
    setServices(serviceItems);
    setSummary(projectSummary);
    setRecentTelemetry(events);
  }

  useEffect(() => {
    api.health().then(() => setConnectionStatus("connected")).catch(() => setConnectionStatus("unavailable"));
    void Promise.resolve().then(refreshProjects).catch(() => setConnectionStatus("unavailable"));
  }, []);

  useEffect(() => {
    if (!selectedProjectId) { queueMicrotask(() => { setServices([]); setSummary(null); setRecentTelemetry([]); }); return; }
    void Promise.resolve().then(() => refreshProjectDetails(selectedProjectId)).catch((error: Error) => setNotice(error.message));
  }, [selectedProjectId]);

  useEffect(() => {
    if (!selectedProjectId) { queueMicrotask(() => { setMetrics(null); setMetricsError(null); setMetricsLoading(false); }); return; }
    const controller = new AbortController();
    queueMicrotask(() => {
      if (controller.signal.aborted) return;
      setMetricsLoading(true); setMetricsError(null);
      api.metrics(selectedProjectId, metricsRange, controller.signal)
        .then((value) => { if (!controller.signal.aborted) setMetrics(value); })
        .catch((error: Error) => { if (!controller.signal.aborted) setMetricsError(error.message); })
        .finally(() => { if (!controller.signal.aborted) setMetricsLoading(false); });
    });
    return () => controller.abort();
  }, [selectedProjectId, metricsRange, metricsRefreshKey]);

  useEffect(() => {
    if (!selectedProjectId) { queueMicrotask(() => setLiveStatus("offline")); return; }
    let socket: WebSocket | undefined;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
    let metricsRefreshTimer: ReturnType<typeof setTimeout> | undefined;
    let closedByEffect = false;
    let attempts = 0;

    const connect = () => {
      setLiveStatus(attempts ? "reconnecting" : "connecting");
      socket = new WebSocket(telemetryWebSocketUrl(selectedProjectId));
      socket.onopen = () => { attempts = 0; setLiveStatus("live"); };
      socket.onmessage = (message) => {
        const payload = JSON.parse(message.data) as { type?: string };
        if (payload.type === "telemetry.created") {
          refreshProjectDetails(selectedProjectId).catch((error: Error) => setNotice(error.message));
          if (metricsRefreshTimer) clearTimeout(metricsRefreshTimer);
          metricsRefreshTimer = setTimeout(() => setMetricsRefreshKey((current) => current + 1), 500);
        }
      };
      socket.onclose = () => {
        if (closedByEffect) return;
        attempts += 1;
        if (attempts > 5) { setLiveStatus("offline"); return; }
        reconnectTimer = setTimeout(connect, Math.min(1000 * 2 ** (attempts - 1), 8000));
      };
      socket.onerror = () => socket?.close();
    };

    connect();
    return () => { closedByEffect = true; if (reconnectTimer) clearTimeout(reconnectTimer); if (metricsRefreshTimer) clearTimeout(metricsRefreshTimer); socket?.close(); };
  }, [selectedProjectId]);

  async function handleProjectSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const project = await api.createProject({ name: projectName, description: projectDescription || undefined });
      setProjectName(""); setProjectDescription(""); setNotice("Project created.");
      await refreshProjects(); setSelectedProjectId(project.id);
    } catch (error) { setNotice(error instanceof Error ? error.message : "Could not create project"); }
  }

  async function handleServiceSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProjectId) return;
    try {
      await api.createService(selectedProjectId, { name: serviceName, environment });
      setServiceName(""); setNotice("Service created."); await refreshProjectDetails(selectedProjectId);
    } catch (error) { setNotice(error instanceof Error ? error.message : "Could not create service"); }
  }

  async function sendTestTelemetry(eventType: "request" | "error") {
    if (!selectedProjectId || !services[0]) { setNotice("Create a service before sending telemetry."); return; }
    try {
      await api.sendTelemetry(eventType === "request"
        ? { project_id: selectedProjectId, service_id: services[0].id, event_type: "request", duration_ms: 142, status_code: 200 }
        : { project_id: selectedProjectId, service_id: services[0].id, event_type: "error", message: "Development test error", http_method: "GET", http_route: "/development-test" });
      setNotice(`Test ${eventType} sent to ${services[0].name}.`); await refreshProjectDetails(selectedProjectId);
    } catch (error) { setNotice(error instanceof Error ? error.message : "Could not send telemetry"); }
  }

  const isConnected = connectionStatus === "connected";
  const connectionLabel = connectionStatus === "checking" ? "Checking API" : isConnected ? "API Connected" : "API Unavailable";

  return (
    <main className="shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="CloudPulse home"><span className="brand-mark" aria-hidden="true">C</span><span>CloudPulse</span></a>
        <div className={`connection ${isConnected ? "connection--online" : ""}`} aria-live="polite"><span className="connection-dot" />{connectionLabel}</div>
        <div className={`live-status live-status--${liveStatus}`} aria-live="polite"><span className="connection-dot" />{liveStatus === "live" ? "Live" : liveStatus[0].toUpperCase() + liveStatus.slice(1)}</div>
      </header>
      <section id="top" className="intro" aria-labelledby="page-title">
        <p className="eyebrow">Observability workspace</p>
        <h1 id="page-title">Real-time visibility into your applications.</h1>
        <p className="intro-copy">A clear starting point for monitoring the health of the services you operate.</p>
      </section>
      <section aria-label="System summary">
        <div className="section-heading"><h2>Overview</h2><p>{selectedProject ? `${selectedProject.name} telemetry` : "Select a project"}</p></div>
        <div className="summary-grid">
          <article className="summary-card"><p>System Status</p><strong className={summary?.status === "healthy" ? "healthy" : summary ? "degraded" : undefined}>{summary?.status ?? "—"}</strong></article>
          <article className="summary-card"><p>Requests</p><strong>{summary?.total_requests ?? 0}</strong></article>
          <article className="summary-card"><p>Average Latency</p><strong>{summary?.average_latency_ms ?? 0} ms</strong></article>
          <article className="summary-card"><p>Error Rate</p><strong>{summary?.error_rate ?? 0}%</strong></article>
        </div>
      </section>
      <section className="metrics-controls" aria-label="Historical metrics time range">
        <div><h2>Telemetry trends</h2><p className="muted">Historical buckets are calculated from PostgreSQL.</p></div>
        <div className="range-selector" role="group" aria-label="Select historical metrics time range">
          {(["15m", "1h", "24h", "7d"] as MetricsTimeRange[]).map((range) => <button className={metricsRange === range ? "selected" : "secondary"} type="button" aria-pressed={metricsRange === range} key={range} onClick={() => setMetricsRange(range)}>{{ "15m": "Last 15 Minutes", "1h": "Last Hour", "24h": "Last 24 Hours", "7d": "Last 7 Days" }[range]}</button>)}
        </div>
      </section>
      <MetricsCharts metrics={metrics} loading={metricsLoading} error={metricsError} />
      <section className="workspace" aria-label="Project setup">
        <div className="panel"><div className="section-heading"><h2>Monitored Projects</h2><p>{projects.length} total</p></div>
          <form className="form" onSubmit={handleProjectSubmit}><input required value={projectName} onChange={(event) => setProjectName(event.target.value)} placeholder="Project name" aria-label="Project name" /><input value={projectDescription} onChange={(event) => setProjectDescription(event.target.value)} placeholder="Description (optional)" aria-label="Project description" /><button type="submit">Create project</button></form>
          <div className="project-list">{projects.length ? projects.map((project) => <button className={`project-item ${project.id === selectedProjectId ? "selected" : ""}`} key={project.id} onClick={() => setSelectedProjectId(project.id)}><span>{project.name}</span><small>{project.description || "No description"}</small></button>) : <p className="muted">No projects yet. Create one to get started.</p>}</div>
        </div>
        <div className="panel services" aria-labelledby="services-title"><div className="section-heading"><h2 id="services-title">Services</h2><p>{selectedProject ? selectedProject.name : "No project selected"}</p></div>
          {selectedProject && <form className="form compact" onSubmit={handleServiceSubmit}><input required value={serviceName} onChange={(event) => setServiceName(event.target.value)} placeholder="Service name" aria-label="Service name" /><input required value={environment} onChange={(event) => setEnvironment(event.target.value)} placeholder="Environment" aria-label="Environment" /><button type="submit">Add service</button></form>}
          <div className="service-list">{selectedProject ? services.length ? services.map((service) => <div className="service-item" key={service.id}><span>{service.name}</span><small>{service.environment}</small></div>) : <p className="muted">No services connected yet.</p> : <p className="muted">Select a project to manage its services.</p>}</div>
        </div>
      </section>
      <section className="demo panel" aria-labelledby="demo-title"><div><p className="eyebrow">Development demo</p><h2 id="demo-title">Send real test telemetry</h2><p className="muted">Sends to the first service in the selected project and refreshes its summary.</p></div><div className="demo-actions"><button disabled={!selectedProjectId || !services.length} onClick={() => sendTestTelemetry("request")}>Send Test Request</button><button className="secondary" disabled={!selectedProjectId || !services.length} onClick={() => sendTestTelemetry("error")}>Send Test Error</button></div></section>
      <section className="recent panel" aria-labelledby="recent-title">
        <div className="section-heading"><h2 id="recent-title">Recent Telemetry</h2><p>Last 10 events</p></div>
        {recentTelemetry.length ? <div className="telemetry-list">
          {recentTelemetry.map((event) => {
            const serviceName = services.find((service) => service.id === event.service_id)?.name ?? "Unknown service";
            const hasHttpDetails = event.http_method || event.http_route;
            const isServerError = event.status_code !== null && event.status_code >= 500;
            return <article className="telemetry-card" key={event.id}>
              <div className="telemetry-card__topline">
                <span className={`event-type event-type--${event.event_type}`}>{event.event_type}</span>
                <span className="telemetry-service">{serviceName}</span>
                <time dateTime={event.timestamp}>{new Date(event.timestamp).toLocaleString()}</time>
              </div>
              <div className="telemetry-card__details">
                <div><span>HTTP</span><strong>{hasHttpDetails ? <>{event.http_method ?? "—"} {event.http_route ?? "—"}</> : "Not provided"}</strong></div>
                <div><span>Status</span><strong className={isServerError ? "status-error" : "status-ok"}>{event.status_code ?? "—"}</strong></div>
                <div><span>Latency</span><strong>{event.duration_ms === null ? "—" : `${event.duration_ms} ms`}</strong></div>
              </div>
              {event.message && <p className="telemetry-message">{event.message}</p>}
            </article>;
          })}
        </div> : <p className="muted">No telemetry received for this project yet.</p>}
      </section>
      {notice && <p className="notice" role="status">{notice}</p>}
    </main>
  );
}
