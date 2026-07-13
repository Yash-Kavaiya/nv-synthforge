"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowRight, BriefcaseBusiness, Building2, Check, CircleDollarSign, Clock3, FileCheck2, FileText, Headphones, HeartPulse, Landmark, LoaderCircle, Scale, ScanText, ShoppingBag, Sparkles, TrendingUp, Users } from "lucide-react";
import { api } from "@/lib/api";
import { fallbackDomains, fallbackGallery } from "@/lib/mock-data";
import type { Domain, GalleryDocument } from "@/lib/types";
import { formatCompact, formatRelative } from "@/lib/format";
import { Badge, Card, SectionHeading, Skeleton } from "./ui";

const domainIcons = { invoices: FileText, healthcare: HeartPulse, legal: Scale, support: Headphones, finance: Landmark, hr: Users, retail: ShoppingBag };
const trend = [44, 58, 52, 66, 62, 74, 70, 83, 78, 91, 86, 98];

export function DashboardOverview() {
  const [domains, setDomains] = useState<Domain[]>([]);
  const [gallery, setGallery] = useState<GalleryDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [demo, setDemo] = useState(false);

  useEffect(() => {
    let active = true;
    Promise.all([api.domains(), api.gallery()])
      .then(([remoteDomains, remoteGallery]) => {
        if (!active) return;
        const byId = new Map(remoteDomains.map((domain) => [domain.id, domain]));
        setDomains(fallbackDomains.map((domain) => byId.get(domain.id) ?? domain));
        setGallery(remoteGallery);
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

  const generated = useMemo(() => domains.reduce((sum, domain) => sum + domain.generated, 0), [domains]);

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
              <Metric icon={ScanText} label="Documents generated" value={formatCompact(generated || 56240)} change="+18.6%" detail="this cycle" />
              <Metric icon={FileCheck2} label="Validation pass rate" value="98.4%" change="+1.2%" detail="across all domains" />
              <Metric icon={Clock3} label="Median generation" value="1.84s" change="−220ms" detail="per document" />
              <Metric icon={CircleDollarSign} label="Compute efficiency" value="₹0.42" change="−8.3%" detail="per 1K tokens" />
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
                {domain.available ? <Link href={`/studio?domain=${domain.id === "healthcare" ? "healthcare" : domain.id === "support" ? "support" : "invoices"}`} className="domain-link">Configure workbench <ArrowRight aria-hidden="true" /></Link> : <span className="domain-link domain-link-muted">Schema calibration in progress</span>}
              </Card>
            );
          })}
        </div>
      </section>

      <section className="dashboard-lower">
        <Card className="throughput-card">
          <SectionHeading eyebrow="12 WEEK SIGNAL" title="Generation throughput" action={<span className="signal-legend"><i /> DOCUMENTS</span>} />
          <div className="chart-summary"><strong>56,240</strong><span><TrendingUp aria-hidden="true" /> 18.6% vs prior cycle</span></div>
          <div className="bar-chart" role="img" aria-label="Weekly document generation increased from 44 to 98 percent of capacity over twelve weeks">
            {trend.map((height, index) => <span key={index} style={{ height: `${height}%` }}><i>{index + 1}</i></span>)}
          </div>
          <div className="chart-axis"><span>APR 21</span><span>MAY 19</span><span>JUN 16</span><span>JUL 13</span></div>
        </Card>
        <Card className="activity-card">
          <SectionHeading eyebrow="JOB STREAM" title="Recent output" action={<Link href="/gallery" className="text-link">View gallery <ArrowRight aria-hidden="true" /></Link>} />
          <div className="activity-list">
            {(gallery.length ? gallery : fallbackGallery).slice(0, 3).map((item) => (
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

function Metric({ icon: Icon, label, value, change, detail }: { icon: typeof ScanText; label: string; value: string; change: string; detail: string }) {
  return (
    <Card className="metric-card">
      <div className="metric-label"><Icon aria-hidden="true" /><span>{label}</span></div>
      <strong>{value}</strong>
      <div className="metric-change"><span>{change}</span> {detail}</div>
      <i className="metric-notch" aria-hidden="true" />
    </Card>
  );
}
