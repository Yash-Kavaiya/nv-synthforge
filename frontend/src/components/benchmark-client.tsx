"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Activity, BarChart3, CheckCircle2, Clock3, FlaskConical, Gauge, LoaderCircle, Play, RefreshCw, ShieldCheck, Sparkles, Zap } from "lucide-react";
import { api } from "@/lib/api";
import { formatRelative } from "@/lib/format";
import type { BenchmarkResult } from "@/lib/types";
import { Badge, Button, Card, EmptyState, Skeleton } from "./ui";

const demoBenchmarks: BenchmarkResult[] = [
  { id: "demo-invoice", name: "Labeled demo · Indian GST invoice quality", domain: "invoices", metricScope: "GST state, subtotal, tax, and grand-total consistency", score: 98.4, latencyMs: 142.5, throughput: 7.2, createdAt: "2026-07-12T08:30:00Z" },
  { id: "demo-clinical", name: "Labeled demo · Clinical note quality", domain: "healthcare", metricScope: "SOAP completeness, ICD-10, and vital-sign consistency", score: 97.8, latencyMs: 118.2, throughput: 8.4, createdAt: "2026-07-11T11:10:00Z" },
  { id: "demo-support", name: "Labeled demo · Support conversation quality", domain: "support", metricScope: "turn structure, resolution, and sentiment-arc consistency", score: 99.1, latencyMs: 96.4, throughput: 10.1, createdAt: "2026-07-10T09:45:00Z" },
  { id: "demo-legal", name: "Labeled demo · Legal contract quality", domain: "legal", metricScope: "synthetic parties, clause structure, and confidentiality consistency", score: 98.9, latencyMs: 104.3, throughput: 9.2, createdAt: "2026-07-09T14:20:00Z" },
  { id: "demo-finance", name: "Labeled demo · Finance statement quality", domain: "finance", metricScope: "period window and debit/credit reconciliation", score: 98.2, latencyMs: 88.1, throughput: 11.4, createdAt: "2026-07-08T16:05:00Z" },
  { id: "demo-hr", name: "Labeled demo · HR record quality", domain: "hr", metricScope: "employee identity and section structure", score: 97.6, latencyMs: 92.7, throughput: 10.8, createdAt: "2026-07-07T12:40:00Z" },
  { id: "demo-retail", name: "Labeled demo · Retail product quality", domain: "retail", metricScope: "SKU pattern, pricing, and review-rating consistency", score: 99.0, latencyMs: 79.5, throughput: 12.6, createdAt: "2026-07-06T10:15:00Z" },
];

export function BenchmarkClient() {
  const [results, setResults] = useState<BenchmarkResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [demo, setDemo] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setResults(await api.benchmarks());
      setDemo(false);
    } catch (cause) {
      setResults(demoBenchmarks);
      setDemo(true);
      setError(cause instanceof Error ? cause.message : "Unable to reach benchmark API");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  const summary = useMemo(() => {
    if (!results.length) return { score: 0, latency: 0, throughput: 0, domains: 0 };
    return {
      score: results.reduce((total, result) => total + result.score, 0) / results.length,
      latency: results.reduce((total, result) => total + result.latencyMs, 0) / results.length,
      throughput: results.reduce((total, result) => total + result.throughput, 0) / results.length,
      domains: new Set(results.map((result) => result.domain)).size,
    };
  }, [results]);

  async function runBenchmark() {
    setRunning(true);
    setError("");
    try {
      const created = await api.benchmark({});
      setResults((current) => [created, ...current.filter((result) => result.id !== created.id)]);
      setDemo(false);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Benchmark failed");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="page-stack benchmark-page">
      <section className="route-header">
        <div>
          <p className="eyebrow">EVALUATION PLANE / CROSS-DOMAIN</p>
          <h1>Quality Benchmarks</h1>
          <p>Compare deterministic validity, generation latency, and throughput across all seven synthetic domains.</p>
        </div>
        <div className="route-header-actions">
          <Button onClick={() => void load()} disabled={loading}><RefreshCw className={loading ? "animate-spin" : ""} aria-hidden="true" /> Refresh</Button>
          <Button className="button-primary" onClick={() => void runBenchmark()} disabled={running || loading}>
            {running ? <LoaderCircle className="animate-spin" aria-hidden="true" /> : <Play aria-hidden="true" />}
            {running ? "Running…" : "Run latest dataset"}
          </Button>
        </div>
      </section>

      {demo ? <div className="notice notice-demo" role="status"><FlaskConical aria-hidden="true" /><div><strong>Labeled demonstration metrics</strong><span>{error}. Generate any supported dataset and reconnect the API to create measured cross-domain results.</span></div></div> : null}
      {!demo && error ? <div className="notice notice-error" role="alert"><Activity aria-hidden="true" /><div><strong>Benchmark could not run</strong><span>{error}</span></div></div> : null}

      <section className="metric-grid" aria-label="Benchmark summary">
        <Metric icon={<ShieldCheck />} label="Mean quality" value={`${summary.score.toFixed(1)}%`} detail="Domain-specific deterministic rules" />
        <Metric icon={<Clock3 />} label="Mean latency" value={`${summary.latency.toFixed(1)} ms`} detail="Per generated record" />
        <Metric icon={<Zap />} label="Throughput" value={`${summary.throughput.toFixed(1)} records/s`} detail="Local pipeline measurement" />
        <Metric icon={<Gauge />} label="Domain coverage" value={`${summary.domains} / 3`} detail={`${results.length} ${demo ? "demonstration" : "persisted"} runs`} />
      </section>

      <div className="benchmark-grid">
        <Card className="benchmark-history">
          <div className="section-heading"><div><p className="eyebrow">RUN HISTORY</p><h2>Measured evaluations</h2></div><Badge tone={demo ? "warning" : "accent"}>{demo ? "DEMO" : "LIVE"}</Badge></div>
          {loading ? <div className="benchmark-skeletons"><Skeleton className="h-36" /><Skeleton className="h-36" /></div> : results.length ? (
            <div className="benchmark-list">
              {results.map((result) => <BenchmarkRow key={result.id} result={result} />)}
            </div>
          ) : (
            <EmptyState icon={<BarChart3 />} title="No benchmark runs yet" description="Generate a supported dataset, then run its deterministic benchmark." action={<Link href="/studio" className="button button-primary"><Sparkles /> Generate dataset</Link>} />
          )}
        </Card>

        <Card className="benchmark-method">
          <p className="eyebrow">METHODOLOGY / V1.2</p>
          <h2>Truthful Score Contract</h2>
          <p>The harness applies a common quality contract across domain-specific rule sets. It reports reproducible pipeline integrity—not subjective or fabricated model accuracy.</p>
          <ul className="methodology-list">
            <li>
              <div className="methodology-item">
                <CheckCircle2 />
                <div><strong>Invoices</strong><span>GST arithmetic, date logic, address alignment, and line-item integrity.</span></div>
              </div>
            </li>
            <li>
              <div className="methodology-item">
                <CheckCircle2 />
                <div><strong>Healthcare</strong><span>SOAP structure, ICD-10 presence, patient identity safety, and vital-sign coherence.</span></div>
              </div>
            </li>
            <li>
              <div className="methodology-item">
                <CheckCircle2 />
                <div><strong>Support</strong><span>Role alternation, sentiment progression, resolution state, and industry coherence.</span></div>
              </div>
            </li>
            <li><CheckCircle2 /> <div><strong>Common</strong><span>Pydantic schema conformance and synthetic provenance safety.</span></div></li>
          </ul>
          <div className="schema-note"><FlaskConical /><div><strong>Adapter roadmap</strong><span>Accept OCR/VLM predictions, align them with ground truth, and compute CER plus field-level precision/recall/F1.</span></div></div>
        </Card>
      </div>
    </div>
  );
}

function Metric({ icon, label, value, detail }: { icon: React.ReactNode; label: string; value: string; detail: string }) {
  return <Card className="metric-card"><div className="metric-notch" /><div className="metric-label">{icon}<span>{label}</span></div><strong>{value}</strong><p>{detail}</p></Card>;
}

function BenchmarkRow({ result }: { result: BenchmarkResult }) {
  return (
    <article className="benchmark-row">
      <div className="score-ring" style={{ "--score": `${result.score * 3.6}deg` } as React.CSSProperties}><span>{result.score.toFixed(1)}</span></div>
      <div className="benchmark-copy"><div className="benchmark-title"><strong>{result.name}</strong><Badge>{result.domain.toUpperCase()}</Badge></div><span>{result.metricScope}</span><small>{result.id} · {formatRelative(result.createdAt)}</small></div>
      <dl><div><dt>Latency</dt><dd>{result.latencyMs.toFixed(1)} ms</dd></div><div><dt>Throughput</dt><dd>{result.throughput.toFixed(1)} rec/s</dd></div></dl>
    </article>
  );
}
