"use client";

import type { ReactNode } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { MetricsTimeRange, ProjectMetrics } from "../lib/api";

const rangeLabels: Record<MetricsTimeRange, string> = {
  "15m": "Last 15 Minutes",
  "1h": "Last Hour",
  "24h": "Last 24 Hours",
  "7d": "Last 7 Days",
};

function formatBucketTimestamp(timestamp: string, timeRange: MetricsTimeRange): string {
  const date = new Date(timestamp);
  return timeRange === "7d"
    ? date.toLocaleString([], { weekday: "short", hour: "numeric" })
    : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function ChartFrame({ title, description, children }: { title: string; description: string; children: ReactNode }) {
  return <article className="chart-card">
    <div><h3>{title}</h3><p>{description}</p></div>
    {children}
  </article>;
}

function ChartTooltip({ active, payload, label, timeRange }: { active?: boolean; payload?: Array<{ name?: string; value?: number; color?: string }>; label?: string; timeRange: MetricsTimeRange }) {
  if (!active || !payload?.length || !label) return null;
  return <div className="chart-tooltip">
    <strong>{label}</strong>
    {payload.map((entry) => <span key={entry.name} style={{ color: entry.color }}>{entry.name}: {entry.value?.toFixed(2).replace(/\.00$/, "")}</span>)}
    <small>{rangeLabels[timeRange]}</small>
  </div>;
}

export function MetricsCharts({ metrics, loading, error }: { metrics: ProjectMetrics | null; loading: boolean; error: string | null }) {
  if (loading) return <section className="metrics panel" aria-label="Historical metrics"><p className="muted">Loading historical metrics…</p></section>;
  if (error) return <section className="metrics panel" aria-label="Historical metrics"><p className="metrics-error" role="alert">Could not load historical metrics: {error}</p></section>;
  if (!metrics) return <section className="metrics panel" aria-label="Historical metrics"><p className="muted">Select a project to view historical metrics.</p></section>;

  const hasTelemetry = metrics.buckets.some((bucket) => bucket.request_count || bucket.error_count);
  if (!hasTelemetry) return <section className="metrics panel" aria-label="Historical metrics"><p className="muted">No telemetry was recorded during the selected time range.</p></section>;

  const data = metrics.buckets.map((bucket) => ({ ...bucket, label: formatBucketTimestamp(bucket.timestamp, metrics.time_range) }));
  const common = { data, margin: { top: 12, right: 8, bottom: 4, left: -18 } };
  const axis = <XAxis dataKey="label" minTickGap={28} tick={{ fill: "#8ea2bc", fontSize: 11 }} tickLine={false} axisLine={false} />;
  const tooltip = <Tooltip content={<ChartTooltip timeRange={metrics.time_range} />} />;
  return <section className="metrics panel" aria-label="Historical metrics charts">
    <div className="section-heading"><div><h2>Historical Metrics</h2><p>{rangeLabels[metrics.time_range]} · {metrics.bucket_width_seconds / 60}-minute buckets</p></div></div>
    <div className="charts-grid">
      <ChartFrame title="Request volume" description="Requests and error events per bucket.">
        <ResponsiveContainer width="100%" height={220}><LineChart {...common}>{axis}<YAxis allowDecimals={false} tick={{ fill: "#8ea2bc", fontSize: 11 }} tickLine={false} axisLine={false} /><CartesianGrid stroke="rgba(143,172,210,.14)" vertical={false} />{tooltip}<Legend /><Line type="monotone" dataKey="request_count" name="Requests" stroke="#67b7ff" strokeWidth={2} dot={false} /><Line type="monotone" dataKey="error_count" name="Errors" stroke="#ff9b9b" strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer>
      </ChartFrame>
      <ChartFrame title="Latency" description="Average and continuous P95 request latency.">
        <ResponsiveContainer width="100%" height={220}><LineChart {...common}>{axis}<YAxis unit=" ms" tick={{ fill: "#8ea2bc", fontSize: 11 }} tickLine={false} axisLine={false} /><CartesianGrid stroke="rgba(143,172,210,.14)" vertical={false} />{tooltip}<Legend /><Line type="monotone" dataKey="average_latency_ms" name="Average latency" stroke="#5fe0a3" strokeWidth={2} dot={false} /><Line type="monotone" dataKey="p95_latency_ms" name="P95 latency" stroke="#d6a8ff" strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer>
      </ChartFrame>
      <ChartFrame title="Error rate" description="Explicit errors and 5xx requests as a percentage of events.">
        <ResponsiveContainer width="100%" height={220}><LineChart {...common}>{axis}<YAxis unit="%" domain={[0, "auto"]} tick={{ fill: "#8ea2bc", fontSize: 11 }} tickLine={false} axisLine={false} /><CartesianGrid stroke="rgba(143,172,210,.14)" vertical={false} />{tooltip}<Legend /><Line type="monotone" dataKey="error_rate" name="Error rate" stroke="#ffb168" strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer>
      </ChartFrame>
    </div>
  </section>;
}
