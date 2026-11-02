"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowRight, BriefcaseBusiness, Building2, Check, Clock3, FileCheck2, FileText, Headphones, HeartPulse, Landmark, Layers, LoaderCircle, Scale, ScanText, ShoppingBag, Sparkles, Users } from "lucide-react";
import { api } from "@/lib/api";
import { fallbackDomains, fallbackGallery } from "@/lib/mock-data";
import type { BenchmarkResult, Domain, GalleryDocument } from "@/lib/types";
import { formatCompact, formatRelative } from "@/lib/format";
import { Badge, Card, SectionHeading, Skeleton } from "./ui";

const domainIcons = { invoices: FileText, healthcare: HeartPulse, legal: Scale, support: Headphones, finance: Landmark, hr: Users, retail: ShoppingBag };

function median(values: number[]): number | undefined {
  if (!values.length) return undefined;
  const sorted = [...values].sort((left, right) => left - right);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

export function DashboardOverview() {
  const [domains, setDomains] = useState<Domain[]>([]);
  const [gallery, setGallery] = useState<GalleryDocument[]>([]);
  const [benchmarks, setBenchmarks] = useState<BenchmarkResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [demo, setDemo] = useState(false);

  useEffect(() => {
    let active = true;
    Promise.all([api.domains(), api.gallery(), api.benchmarks().catch(() => [] as BenchmarkResult[])])
      .then(([remoteDomains, remoteGallery, remoteBenchmarks]) => {
        if (!active) return;
        const byId = new Map(remoteDomains.map((domain) => [domain.id, domain]));
        // Keep catalog order and copy from the local catalog, but every number comes from the live API.
        setDomains(fallbackDomains.map((domain) => {
          const live = byId.get(domain.id);
          return live ? { ...domain, ...live } : { ...domain, generated: 0, accuracy: 0 };
        }));
        setGallery(remoteGallery);
        setBenchmarks(remoteBenchmarks);
      })
      .catch(() => {
        if (!active) return;
        setDomains(fallbackDomains);
        setGallery(fallbackGallery);
        setDemo(true);
      })
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, []);

  const stats = useMemo(() => {
    const generated = domains.reduce((sum, domain) => sum + domain.generated, 0);
    const weighted = domains.reduce((sum, domain) => sum + domain.generated * domain.accuracy, 0);
    return {
      generated,
      meanScore: generated ? Math.round((weighted / generated) * 10) / 10 : undefined,
      medianLatency: median(benchmarks.map((item) => item.latencyMs).filter((value) => value > 0)),
      activeDomains: domains.filter((domain) => domain.generated > 0).length,
    };
  }, [domains, benchmarks]);
  const maxGenerated = Math.max(1, ...domains.map((domain) => domain.generated));
  const recent = demo ? fallbackGallery : gallery;

  return (
    <div className="page-stack">
      <section className="page-intro">
        <div>
          <div className="intro-label"><span /> SYNTHETIC DATA CONTROL PLANE</div>
          <h1>Build documents that train<br /><em>production-grade AI.</em></h1>
          <p>Configure, generate, validate, and benchmark domain-specific synthetic data from one precision workspace.</p>
        </div>
        <Link href="/studio" className="button button-primary"><Sparkles aria-hidden="true" /> Open Generation Studio <ArrowRight aria-hidden="true" /></Link>
      </section>

      {demo ? <div className="notice notice-demo" role="status"><Building2 aria-hidden="true" /><div><strong>Demonstration dataset active</strong><span>The API is unavailable at {api.baseUrl}. Controls remain fully explorable with realistic local results.</span></div></div> : null}

      <section aria-labelledby="metrics-title">
        <h2 id="metrics-title" className="sr-only">Workspace metrics</h2>
        <div className="metric-grid">
          {loading ? Array.from({ length: 4 }, (_, index) => <Skeleton key={index} className="h-36" />) : (
            <>
              <Metric icon={ScanText} label="Documents generated" value={formatCompact(stats.generated)} detail={demo ? "demo dataset" : "completed jobs"} />
              <Metric icon={FileCheck2} label="Mean validation score" value={stats.meanScore === undefined ? "—" : `${stats.meanScore}%`} detail="document-weighted" />
              <Metric icon={Clock3} label="Median generation" value={stats.medianLatency === undefined ? "—" : stats.medianLatency >= 1000 ? `${(stats.medianLatency / 1000).toFixed(2)}s` : `${Math.round(stats.medianLatency)}ms`} detail="per document, recent runs" />
              <Metric icon={Layers} label="Active domains" value={`${stats.activeDomains}/${domains.length || 7}`} detail="with generated output" />
            </>
          )}
        </div>
      </section>

      <section>
        <SectionHeading eyebrow="DOMAIN CATALOG" title="Generation workbenches" description="Purpose-built schemas, constraints, and validation rules for high-signal training corpora." action={<Badge tone="neutral">7 DOMAINS</Badge>} />
        <div className="domain-grid">
          {(loading ? fallbackDomains : domains).map((domain, index) => {
            const Icon = domainIcons[domain.id as keyof typeof domainIcons] ?? BriefcaseBusiness;
            return (
              <Card key={domain.id} className={domain.available ? "domain-card domain-available" : "domain-card"}>
                <div className="domain-card-top"><div className="domain-icon"><Icon aria-hidden="true" /></div>{domain.available ? <Badge tone="accent">READY</Badge> : <Badge>PLANNED</Badge>}</div>
                <div><span className="domain-index">0{index + 1}</span><h3>{domain.name}</h3><p>{domain.description}</p></div>
                <div className="domain-stats"><span><small>GENERATED</small><strong>{formatCompact(domain.generated)}</strong></span><span><small>VALIDATION</small><strong>{domain.accuracy ? `${domain.accuracy}%` : "—"}</strong></span></div>
                {domain.available ? <Link href={`/studio?domain=${domain.id === "invoice" ? "invoices" : domain.id}`} className="domain-link">Configure workbench <ArrowRight aria-hidden="true" /></Link> : <span className="domain-link domain-link-muted">Schema calibration in progress</span>}
              </Card>
            );
          })}
        </div>
      </section>

      <section className="dashboard-lower">
        <Card className="throughput-card">
          <SectionHeading eyebrow="DOMAIN SIGNAL" title="Documents by domain" action={<span className="signal-legend"><i /> DOCUMENTS</span>} />
          <div className="chart-summary"><strong>{stats.generated.toLocaleString("en-IN")}</strong><span>{demo ? "demo dataset" : "across completed jobs"}</span></div>
          <div className="bar-chart" role="img" aria-label={`Documents generated per domain: ${domains.map((domain) => `${domain.name} ${domain.generated}`).join(", ")}`}>
            {domains.map((domain) => <span key={domain.id} title={`${domain.name}: ${domain.generated}`} style={{ height: `${Math.max(2, (domain.generated / maxGenerated) * 100)}%` }}><i>{domain.id.slice(0, 3).toUpperCase()}</i></span>)}
          </div>
        </Card>
        <Card className="activity-card">
          <SectionHeading eyebrow="JOB STREAM" title="Recent output" action={<Link href="/gallery" className="text-link">View gallery <ArrowRight aria-hidden="true" /></Link>} />
          <div className="activity-list">
            {!loading && !recent.length ? <p className="empty-copy">No generated documents yet. Run a workbench to populate the job stream.</p> : null}
            {recent.slice(0, 3).map((item) => (
              <Link href="/gallery" key={item.id} className="activity-item">
                <div className="file-glyph"><FileText aria-hidden="true" /></div>
                <div><strong>{item.title}</strong><span>{item.language} · {item.provider} · {formatRelative(item.createdAt)}</span></div>
                <div className="score-mini"><Check aria-hidden="true" /><span>{item.validationScore}</span></div>
              </Link>
            ))}
          </div>
          {loading ? <div className="inline-loading"><LoaderCircle className="animate-spin" aria-hidden="true" /> Syncing job stream</div> : null}
        </Card>
      </section>
    </div>
  );
}

function Metric({ icon: Icon, label, value, detail }: { icon: typeof ScanText; label: string; value: string; detail: string }) {
  return (
    <Card className="metric-card">
      <div className="metric-label"><Icon aria-hidden="true" /><span>{label}</span></div>
      <strong>{value}</strong>
      <div className="metric-change">{detail}</div>
      <i className="metric-notch" aria-hidden="true" />
    </Card>
  );
}
