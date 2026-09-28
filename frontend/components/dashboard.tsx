"use client";

import { useEffect, useState } from "react";

type ConnectionStatus = "checking" | "connected" | "unavailable";

const summaryCards = [
  { label: "System Status", value: "Healthy", accent: true },
  { label: "Requests", value: "0" },
  { label: "Average Latency", value: "0 ms" },
  { label: "Error Rate", value: "0%" },
];

export function Dashboard() {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("checking");

  useEffect(() => {
    const controller = new AbortController();
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
    fetch(`${apiBaseUrl}/health`, { signal: controller.signal })
      .then((response) => setConnectionStatus(response.ok ? "connected" : "unavailable"))
      .catch(() => setConnectionStatus("unavailable"));
    return () => controller.abort();
  }, []);

  const isConnected = connectionStatus === "connected";
  const connectionLabel = connectionStatus === "checking" ? "Checking API" : isConnected ? "API Connected" : "API Unavailable";

  return (
    <main className="shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="CloudPulse home"><span className="brand-mark" aria-hidden="true">C</span><span>CloudPulse</span></a>
        <div className={`connection ${isConnected ? "connection--online" : ""}`} aria-live="polite"><span className="connection-dot" />{connectionLabel}</div>
      </header>
      <section id="top" className="intro" aria-labelledby="page-title">
        <p className="eyebrow">Observability workspace</p>
        <h1 id="page-title">Real-time visibility into your applications.</h1>
        <p className="intro-copy">A clear starting point for monitoring the health of the services you operate.</p>
      </section>
      <section aria-label="System summary">
        <div className="section-heading"><h2>Overview</h2><p>Current service telemetry</p></div>
        <div className="summary-grid">
          {summaryCards.map((card) => <article className="summary-card" key={card.label}><p>{card.label}</p><strong className={card.accent ? "healthy" : undefined}>{card.value}</strong></article>)}
        </div>
      </section>
      <section className="services" aria-labelledby="services-title">
        <div className="section-heading"><h2 id="services-title">Services</h2><p>Connected applications</p></div>
        <div className="empty-state"><span className="empty-icon" aria-hidden="true">+</span><p>No services connected yet.</p><span>Connect a service to begin receiving telemetry.</span></div>
      </section>
    </main>
  );
}
