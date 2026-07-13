"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  Archive,
  CircleAlert,
  Download,
  Eye,
  FileJson,
  FileText,
  Filter,
  Image as ImageIcon,
  RefreshCw,
  Search,
  Sparkles,
  X,
} from "lucide-react";
import { api } from "@/lib/api";
import { formatRelative, scoreTone } from "@/lib/format";
import { fallbackGallery } from "@/lib/mock-data";
import type { GalleryDocument, Language } from "@/lib/types";
import { DocumentPreview } from "./document-preview";
import { ValidationRules } from "./invoice-preview";
import { Badge, Button, Card, EmptyState, Skeleton, cn } from "./ui";

const languageLabels: Record<Language, string> = {
  "en-IN": "English",
  "hi-IN": "Hindi",
  "gu-IN": "Gujarati",
};

type GalleryStatus = "all" | GalleryDocument["status"];

export function GalleryClient() {
  const searchParams = useSearchParams();
  const [documents, setDocuments] = useState<GalleryDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [demo, setDemo] = useState(false);
  const [error, setError] = useState("");
  const [query, setQuery] = useState(searchParams.get("q") ?? "");
  const [language, setLanguage] = useState<"all" | Language>("all");
  const [status, setStatus] = useState<GalleryStatus>("all");
  const [selected, setSelected] = useState<GalleryDocument | null>(null);

  const loadGallery = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const remote = await api.gallery();
      setDocuments(remote);
      setDemo(false);
    } catch (loadError) {
      setDocuments(fallbackGallery);
      setDemo(true);
      setError(loadError instanceof Error ? loadError.message : "Unable to load gallery");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadGallery(), 0);
    return () => window.clearTimeout(timer);
  }, [loadGallery]);

  const filtered = useMemo(() => {
    const search = query.trim().toLowerCase();
    return documents.filter((document) => {
      const searchFields = [document.title, document.id, document.vendor, document.invoiceNumber, document.medicalNote?.note_id, document.medicalNote?.patient.name, document.medicalNote?.chief_complaint, document.medicalNote?.diagnoses[0]?.icd10_code, document.conversation?.conversation_id, document.conversation?.customer_id, document.conversation?.issue_type, document.conversation?.industry, ...(document.conversation?.turns.map((turn) => turn.text) ?? []), document.contract?.contract_id, document.contract?.title, document.contract?.document_type, document.contract?.governing_law, ...(document.contract?.parties.map((party) => party.name) ?? []), ...(document.contract?.clauses.map((clause) => `${clause.title} ${clause.body}`) ?? []), document.statement?.statement_id, document.statement?.entity_name, document.statement?.statement_type, ...(document.statement?.line_items.map((line) => line.label) ?? []), document.hrRecord?.record_id, document.hrRecord?.employee_name, document.hrRecord?.role_title, document.hrRecord?.department, ...(document.hrRecord?.sections.map((section) => `${section.title} ${section.body}`) ?? []), document.product?.product_id, document.product?.sku, document.product?.title, document.product?.brand, document.product?.category, ...(document.product?.reviews.map((review) => `${review.title} ${review.body}`) ?? [])];
      const matchesQuery = !search || searchFields
        .filter(Boolean)
        .some((value) => value?.toLowerCase().includes(search));
      return matchesQuery
        && (language === "all" || document.language === language)
        && (status === "all" || document.status === status);
    });
  }, [documents, language, query, status]);

  return (
    <div className="page-stack gallery-page">
      <section className="route-header">
        <div>
          <p className="eyebrow">ARTIFACT REGISTRY / MULTI-DOMAIN</p>
          <h1>Results Gallery</h1>
          <p>Review generated documents, inspect validation evidence, and export artifacts.</p>
        </div>
        <div className="route-header-actions">
          <Button onClick={() => void loadGallery()} disabled={loading}>
            <RefreshCw className={loading ? "animate-spin" : ""} aria-hidden="true" /> Refresh
          </Button>
          <Link href="/studio" className="button button-primary"><Sparkles aria-hidden="true" /> New generation</Link>
        </div>
      </section>

      {demo ? (
        <div className="notice notice-demo" role="status">
          <Archive aria-hidden="true" />
          <div>
            <strong>Demo gallery — not live API output</strong>
            <span>{error}. Showing a labeled local sample so the review workflow remains usable.</span>
          </div>
        </div>
      ) : null}

      <Card className="filter-bar">
        <label className="filter-search">
          <Search aria-hidden="true" />
          <span className="sr-only">Search gallery</span>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search conversation, patient, vendor, or ID" />
          {query ? <button type="button" onClick={() => setQuery("")} aria-label="Clear search"><X aria-hidden="true" /></button> : null}
        </label>
        <div className="filter-selects">
          <label><Filter aria-hidden="true" /><span className="sr-only">Filter by language</span><select value={language} onChange={(event) => setLanguage(event.target.value as "all" | Language)}><option value="all">All languages</option>{Object.entries(languageLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
          <label><span className="sr-only">Filter by validation status</span><select value={status} onChange={(event) => setStatus(event.target.value as GalleryStatus)}><option value="all">All validation states</option><option value="validated">Validated</option><option value="review">Needs review</option></select></label>
        </div>
        <span className="result-count" aria-live="polite">{loading ? "Syncing…" : `${filtered.length} result${filtered.length === 1 ? "" : "s"}`}</span>
      </Card>

      {loading ? (
        <div className="gallery-grid" aria-label="Loading gallery">
          {Array.from({ length: 6 }, (_, index) => <Skeleton key={index} className="gallery-skeleton" />)}
        </div>
      ) : filtered.length ? (
        <div className="gallery-grid">
          {filtered.map((document) => (
            <GalleryCard key={document.id} document={document} demo={demo} onInspect={() => setSelected(document)} />
          ))}
        </div>
      ) : (
        <Card>
          <EmptyState
            icon={<FileText aria-hidden="true" />}
            title="No documents match"
            description="Clear a filter or generate a new synthetic dataset."
            action={<button type="button" className="button" onClick={() => { setQuery(""); setLanguage("all"); setStatus("all"); }}>Clear filters</button>}
          />
        </Card>
      )}

      {selected ? <DocumentDetail document={selected} demo={demo} onClose={() => setSelected(null)} /> : null}
    </div>
  );
}

function GalleryCard({ document, demo, onInspect }: { document: GalleryDocument; demo: boolean; onInspect: () => void }) {
  const passedRules = document.rules.filter((rule) => rule.passed).length;
  const identifier = document.conversation?.conversation_id ?? document.medicalNote?.note_id ?? document.invoiceNumber;
  const summary = document.conversation
    ? `${document.conversation.industry} · ${document.conversation.issue_type}`
    : document.medicalNote
      ? `${document.medicalNote.diagnoses[0]?.icd10_code ?? "ICD"} · ${document.medicalNote.patient.name}`
      : document.amount ?? "Amount unavailable";
  return (
    <Card className="gallery-card">
      <button type="button" className="gallery-preview-button" onClick={onInspect} aria-label={`Inspect ${document.title}`}>
        <DocumentPreview document={document} compact />
        <span className="preview-hover"><Eye aria-hidden="true" /> Inspect artifact</span>
      </button>
      <div className="gallery-card-body">
        <div className="gallery-card-meta">
          <Badge tone={document.status === "validated" ? "accent" : "warning"}>{document.status === "validated" ? "VALIDATED" : "REVIEW"}</Badge>
          {demo ? <Badge>DEMO</Badge> : null}
          <span>{formatRelative(document.createdAt)}</span>
        </div>
        <h2>{document.title}</h2>
        <p>{identifier} · {languageLabels[document.language]} · {document.provider}</p>
        <div className="gallery-score-row">
          <div className={cn("quality-orb", `quality-${scoreTone(document.validationScore)}`)}><strong>{document.validationScore}</strong><span>/100</span></div>
          <div><strong>{passedRules}/{document.rules.length} rules passed</strong><span>{summary}</span></div>
          <button type="button" className="icon-button" onClick={onInspect} aria-label={`Open ${document.title}`}><Eye aria-hidden="true" /></button>
        </div>
      </div>
    </Card>
  );
}

function DocumentDetail({ document, demo, onClose }: { document: GalleryDocument; demo: boolean; onClose: () => void }) {
  return (
    <div className="detail-overlay" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="detail-panel" role="dialog" aria-modal="true" aria-labelledby="detail-title">
        <header>
          <div><p className="eyebrow">ARTIFACT / {document.id}</p><h2 id="detail-title">{document.title}</h2></div>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Close artifact details"><X aria-hidden="true" /></button>
        </header>
        {demo ? <div className="demo-ribbon"><CircleAlert aria-hidden="true" /> Local demonstration artifact — no server file is implied.</div> : null}
        <div className="detail-grid">
          <div className="detail-preview"><DocumentPreview document={document} /></div>
          <aside>
            <div className="detail-score"><div className={cn("quality-orb", `quality-${scoreTone(document.validationScore)}`)}><strong>{document.validationScore}</strong><span>/100</span></div><div><span>Validation score</span><strong>{document.status === "validated" ? "Release ready" : "Manual review"}</strong></div></div>
            <dl className="artifact-meta">
              <div><dt>Language</dt><dd>{languageLabels[document.language]}</dd></div><div><dt>Provider</dt><dd>{document.provider}</dd></div>
              {document.conversation ? <><div><dt>Customer</dt><dd>{document.conversation.customer_id}</dd></div><div><dt>Resolution</dt><dd>{document.conversation.resolution_status}</dd></div></> : document.medicalNote ? <><div><dt>Patient</dt><dd>{document.medicalNote.patient.name}</dd></div><div><dt>Diagnosis</dt><dd>{document.medicalNote.diagnoses[0]?.icd10_code ?? "—"}</dd></div></> : <><div><dt>Invoice</dt><dd>{document.invoiceNumber}</dd></div><div><dt>Total</dt><dd>{document.amount}</dd></div></>}
            </dl>
            <h3>Validation evidence</h3>
            <ValidationRules document={document} />
            <div className="download-stack">
              <ArtifactButton label="PDF" icon={<FileText />} href={document.fileUrls.pdf} />
              <ArtifactButton label="PNG" icon={<ImageIcon />} href={document.fileUrls.image} />
              <ArtifactButton label="JSON" icon={<FileJson />} href={document.fileUrls.json} onFallback={() => downloadManifest(document)} />
            </div>
            {!document.fileUrls.pdf && !document.fileUrls.image ? <p className="artifact-hint">Rendered server files are not available for this artifact. The normalized JSON manifest can still be downloaded.</p> : null}
          </aside>
        </div>
      </section>
    </div>
  );
}

function ArtifactButton({ label, icon, href, onFallback }: { label: string; icon: React.ReactNode; href?: string; onFallback?: () => void }) {
  if (href) return <a className="button" href={href} target="_blank" rel="noreferrer" download>{icon}<Download aria-hidden="true" /> {label}</a>;
  return <button type="button" className="button" disabled={!onFallback} onClick={onFallback}>{icon}<Download aria-hidden="true" /> {label}</button>;
}

function downloadManifest(document: GalleryDocument) {
  const blob = new Blob([JSON.stringify(document, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = window.document.createElement("a");
  anchor.href = url;
  anchor.download = `${document.id}.json`;
  anchor.click();
  URL.revokeObjectURL(url);
}
