"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Braces, Check, ChevronDown, CircleAlert, CloudCog, Cpu, Download, Eye, FileJson2, Gauge, Languages, LoaderCircle, RotateCcw, ShieldCheck, Sparkles, WandSparkles } from "lucide-react";
import { api } from "@/lib/api";
import { fallbackGallery } from "@/lib/mock-data";
import type { ClinicalProfile, DomainId, FinanceStatementType, GenerateRequest, HRDocumentType, Job, Language, LegalDocumentType, Provider, RetailCategory, SentimentArc, SupportIndustry } from "@/lib/types";
import { DocumentPreview } from "./document-preview";
import { ValidationRules } from "./invoice-preview";
import { Badge, Button, Card, cn } from "./ui";

const invoiceDefaults: GenerateRequest = {
  domain: "invoices",
  count: 25,
  seed: 260713,
  provider: "offline",
  language: "en-IN",
  render: true,
  degrade: true,
  degradation: { noise: 0.18, blur: 0.08, perspective: 0.12, stamps: 0.24 },
  healthcare: { clinical_profile: "mixed", include_medications: true },
  support: { industry: "mixed", sentiment_arc: "recovery", max_turns: 6 },
  legal: { document_type: "mixed", max_clauses: 6 },
  finance: { statement_type: "mixed", max_lines: 6 },
  hr: { document_type: "mixed", max_sections: 4 },
  retail: { category: "mixed", max_reviews: 3 },
};

function defaultsFor(domain: DomainId): GenerateRequest {
  const shared = {
    ...invoiceDefaults,
    domain,
    degradation: { ...invoiceDefaults.degradation },
    healthcare: { ...invoiceDefaults.healthcare },
    support: { ...invoiceDefaults.support },
    legal: { ...invoiceDefaults.legal },
    finance: { ...invoiceDefaults.finance },
    hr: { ...invoiceDefaults.hr },
    retail: { ...invoiceDefaults.retail },
  };
  return domain === "invoices"
    ? shared
    : { ...shared, count: 10, render: false, degrade: false };
}

const labels: Record<Language, string> = { "en-IN": "English", "hi-IN": "हिन्दी", "gu-IN": "ગુજરાતી" };

const DOMAIN_META: Record<DomainId, { label: string; workbench: string; title: string; description: string; schema: string; noun: string; validation: string }> = {
  invoices: { label: "Invoices", workbench: "INVOICE WORKBENCH / V1.4", title: "Invoice Studio", description: "Compose a reproducible synthetic document run, then inspect every validation signal.", schema: "invoice.india.v4", noun: "invoices", validation: "GST arithmetic, date logic, addresses, currencies, and line-item integrity are checked before output." },
  healthcare: { label: "Healthcare", workbench: "HEALTHCARE WORKBENCH / V1.0", title: "Clinical Note Studio", description: "Generate privacy-safe synthetic SOAP notes with pseudonymous identities and clinical validation.", schema: "clinical.soap.v1", noun: "clinical notes", validation: "Synthetic labeling, pseudonymous identity, SOAP completeness, ICD-10 presence, and vital-sign consistency are checked before output." },
  support: { label: "Support", workbench: "SUPPORT WORKBENCH / V1.0", title: "Conversation Studio", description: "Generate deterministic multi-turn service conversations with sentiment and resolution validation.", schema: "support.conversation.v1", noun: "conversations", validation: "Synthetic labeling, pseudonymous identity, turn alternation, resolution state, and sentiment progression are checked before output." },
  legal: { label: "Legal", workbench: "LEGAL WORKBENCH / V1.0", title: "Contract Studio", description: "Generate synthetic NDAs, service agreements, and MSAs with clause libraries and risk flags.", schema: "legal.contract.v1", noun: "contracts", validation: "Synthetic labeling, distinct parties, sequential clauses, confidentiality, and disclaimer presence are checked before output." },
  finance: { label: "Finance", workbench: "FINANCE WORKBENCH / V1.0", title: "Statement Studio", description: "Generate synthetic balance sheets, income statements, and cash-flow records with reconciled totals.", schema: "finance.statement.v1", noun: "statements", validation: "Synthetic entity IDs, valid periods, debit/credit reconciliation, and net-position integrity are checked before output." },
  hr: { label: "HR", workbench: "HR WORKBENCH / V1.0", title: "People Studio", description: "Generate synthetic offer letters, performance reviews, and onboarding checklists.", schema: "hr.record.v1", noun: "HR records", validation: "Synthetic employee IDs, positive compensation, sequential sections, and disclaimer presence are checked before output." },
  retail: { label: "Retail", workbench: "RETAIL WORKBENCH / V1.0", title: "Catalog Studio", description: "Generate synthetic product listings with pricing, inventory, and review ratings.", schema: "retail.product.v1", noun: "products", validation: "Synthetic SKUs, pricing consistency, sequential reviews, and rating averages are checked before output." },
};


export function StudioClient({ initialDomain = "invoices" }: { initialDomain?: DomainId }) {
  const initialConfig = defaultsFor(initialDomain);
  const [config, setConfig] = useState(initialConfig);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [advancedJson, setAdvancedJson] = useState(JSON.stringify(initialConfig.degradation, null, 2));
  const [jsonError, setJsonError] = useState("");
  const [job, setJob] = useState<Job | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [demo, setDemo] = useState(false);
  const [error, setError] = useState("");
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => () => { if (intervalRef.current) clearInterval(intervalRef.current); }, []);

  function switchDomain(domain: DomainId) {
    const next = defaultsFor(domain);
    if (intervalRef.current) clearInterval(intervalRef.current);
    setConfig(next);
    setAdvancedJson(JSON.stringify(next.degradation, null, 2));
    setAdvancedOpen(false);
    setJsonError("");
    setError("");
    setDemo(false);
    setJob(null);
  }

  function updateDegradation(key: keyof GenerateRequest["degradation"], value: number) {
    const next = { ...config.degradation, [key]: value };
    setConfig((current) => ({ ...current, degradation: next }));
    setAdvancedJson(JSON.stringify(next, null, 2));
  }

  function simulateDemo(request: GenerateRequest) {
    setDemo(true);
    let progress = 8;
    const id = `demo-${Date.now()}`;
    setJob({ id, status: "queued", progress, message: "Allocating local generation worker", results: [] });
    intervalRef.current = setInterval(() => {
      progress = Math.min(100, progress + Math.ceil(Math.random() * 13));
      setJob({
        id,
        status: progress >= 100 ? "completed" : "running",
        progress,
        message: progress >= 100 ? `${request.count} synthetic ${request.domain === "invoices" ? "invoices validated" : request.domain === "healthcare" ? "clinical notes forged" : request.domain === "legal" ? "contracts drafted" : "conversations synthesized"}` : progress > 68 ? "Running schema and validation checks" : "Rendering document variants",
        results: progress >= 100 ? fallbackGallery.slice(0, Math.min(3, request.count)).map((item, index) => ({ ...item, id: `${id}-${index}`, language: request.language, provider: request.provider, createdAt: new Date().toISOString() })) : [],
      });
      if (progress >= 100 && intervalRef.current) clearInterval(intervalRef.current);
    }, 650);
  }

  function startPolling(id: string) {
    let failures = 0;
    intervalRef.current = setInterval(async () => {
      try {
        const next = await api.job(id);
        failures = 0;
        setJob(next);
        if (next.status === "completed" || next.status === "failed") {
          if (intervalRef.current) clearInterval(intervalRef.current);
          setSubmitting(false);
        }
      } catch {
        failures += 1;
        if (failures >= 3) {
          if (intervalRef.current) clearInterval(intervalRef.current);
          setError("Live job updates were interrupted. The job may still be running on the server.");
          setSubmitting(false);
        }
      }
    }, 1500);
  }

  async function generate() {
    setError("");
    setJsonError("");
    if (intervalRef.current) clearInterval(intervalRef.current);
    let requestConfig = config;
    if (config.domain === "invoices") {
      try {
        const parsed = JSON.parse(advancedJson) as Partial<GenerateRequest["degradation"]>;
        const values = Object.values(parsed);
        if (values.some((value) => typeof value !== "number" || value < 0 || value > 1)) throw new Error();
        requestConfig = { ...config, degradation: { ...config.degradation, ...parsed } };
        setConfig(requestConfig);
      } catch {
        setJsonError("Use valid JSON with numeric degradation values from 0 to 1.");
        if (advancedOpen) return;
      }
    }
    setSubmitting(true);
    setJob(null);
    try {
      const created = await api.generate(requestConfig);
      setJob(created);
      if (created.status === "completed") setSubmitting(false);
      else startPolling(created.id);
    } catch (generationError) {
      if (requestConfig.domain !== "invoices") {
        setError(generationError instanceof Error ? generationError.message : `Unable to reach the ${requestConfig.domain} generation API.`);
        setSubmitting(false);
        return;
      }
      simulateDemo(requestConfig);
      setSubmitting(false);
    }
  }

  function reset() {
    const next = defaultsFor(config.domain);
    setConfig(next);
    setAdvancedJson(JSON.stringify(next.degradation, null, 2));
    setJsonError("");
  }

  const meta = DOMAIN_META[config.domain];
  const isHealthcare = config.domain === "healthcare";
  const isSupport = config.domain === "support";
  const isLegal = config.domain === "legal";
  const isFinance = config.domain === "finance";
  const isHr = config.domain === "hr";
  const isRetail = config.domain === "retail";
  const isStructured = config.domain !== "invoices";
  const workbenchLabel = meta.workbench;
  const studioTitle = meta.title;
  const studioDescription = meta.description;
  const activeResult = job?.results[0];

  return (
    <div className="page-stack studio-page">
      <section className="studio-header">
        <div><p className="eyebrow">{workbenchLabel}</p><h1>{studioTitle}</h1><p>{studioDescription}</p></div>
        <div className="studio-domain-tools">
          <div className="domain-switcher domain-switcher-wide" aria-label="Generation domain">
            {(Object.keys(DOMAIN_META) as DomainId[]).map((domain) => (
              <button key={domain} type="button" className={config.domain === domain ? "segment-active" : ""} aria-pressed={config.domain === domain} onClick={() => switchDomain(domain)}>{DOMAIN_META[domain].label}</button>
            ))}
          </div>
          <div className="studio-header-meta"><Badge tone="accent"><ShieldCheck aria-hidden="true" /> SCHEMA LOCKED</Badge><span>{meta.schema}</span></div>
        </div>
      </section>

      {demo ? <div className="notice notice-demo" role="status"><Cpu aria-hidden="true" /><div><strong>Demo generation worker active</strong><span>The backend could not be reached. This run is simulated locally and is clearly isolated from production output.</span></div></div> : null}
      {error ? <div className="notice notice-error" role="alert"><CircleAlert aria-hidden="true" /><div><strong>Job connection issue</strong><span>{error}</span></div></div> : null}

      <div className="studio-grid">
        <div className="config-column">
          <Card className="config-card">
            <ConfigHeader number="01" icon={<Gauge />} title="Run volume" description="Size and reproducibility controls" />
            <div className="field-block">
              <div className="field-label"><label htmlFor="count">Document count</label><output htmlFor="count">{config.count}</output></div>
              <input id="count" type="range" min="1" max="100" value={config.count} onChange={(event) => setConfig({ ...config, count: Number(event.target.value) })} style={{ "--range-progress": `${config.count}%` } as React.CSSProperties} />
              <div className="range-marks"><span>1</span><span>25</span><span>50</span><span>75</span><span>100</span></div>
            </div>
            <div className="field-block">
              <label htmlFor="seed">Deterministic seed</label>
              <div className="input-with-icon"><Braces aria-hidden="true" /><input id="seed" type="number" value={config.seed} onChange={(event) => setConfig({ ...config, seed: Number(event.target.value) })} /><button aria-label="Generate random seed" onClick={() => setConfig({ ...config, seed: Math.floor(Math.random() * 999999) })}><RotateCcw aria-hidden="true" /></button></div>
              <p className="field-hint">Reuse this seed to reproduce the exact dataset.</p>
            </div>
          </Card>

          <Card className="config-card">
            <ConfigHeader number="02" icon={<Languages />} title="Locale & inference" description="Language and generation provider" />
            <fieldset className="field-block"><legend>Document language</legend><div className="segment-control">{(Object.keys(labels) as Language[]).map((language) => <button type="button" key={language} className={config.language === language ? "segment-active" : ""} onClick={() => setConfig({ ...config, language })} aria-pressed={config.language === language}><strong>{labels[language]}</strong><span>{language}</span></button>)}</div></fieldset>
            <fieldset className="field-block"><legend>Generation provider</legend><div className="provider-grid">
              <button type="button" className={cn("provider-card", config.provider === "offline" && "provider-active")} onClick={() => setConfig({ ...config, provider: "offline" as Provider })} aria-pressed={config.provider === "offline"}><Cpu aria-hidden="true" /><div><strong>Offline forge</strong><span>Fast, private, deterministic</span></div><i>{config.provider === "offline" ? <Check /> : null}</i></button>
              <button type="button" disabled={isStructured} className={cn("provider-card", config.provider === "nemo" && "provider-active", isStructured && "control-disabled")} onClick={() => !isStructured && setConfig({ ...config, provider: "nemo" as Provider })} aria-pressed={config.provider === "nemo"}><CloudCog aria-hidden="true" /><div><strong>NVIDIA NeMo</strong><span>{isStructured ? `${meta.label} adapter calibration pending` : "Higher variation, API-backed"}</span></div><i>{config.provider === "nemo" ? <Check /> : null}</i></button>
            </div></fieldset>
          </Card>

          {isHealthcare ? (
            <Card className="config-card">
              <ConfigHeader number="03" icon={<ShieldCheck />} title="Clinical controls" description="Scenario mix and safety policy" />
              <div className="field-block">
                <label htmlFor="clinical-profile">Clinical profile</label>
                <select id="clinical-profile" className="studio-select" value={config.healthcare.clinical_profile} onChange={(event) => setConfig({ ...config, healthcare: { ...config.healthcare, clinical_profile: event.target.value as ClinicalProfile } })}>
                  <option value="mixed">Mixed primary care</option><option value="respiratory">Respiratory</option><option value="cardiovascular">Cardiovascular</option><option value="general">General medicine</option>
                </select>
                <p className="field-hint">Constrains the scenario and ICD-10 distribution for this run.</p>
              </div>
              <div className="toggle-list"><Toggle label="Include medication plans" detail="Emit synthetic dose, route, frequency, and duration" checked={config.healthcare.include_medications} onChange={(include_medications) => setConfig({ ...config, healthcare: { ...config.healthcare, include_medications } })} /></div>
              <div className="clinical-policy"><ShieldCheck aria-hidden="true" /><div><strong>Privacy policy enforced</strong><span>Pseudonymous patient IDs, synthetic-only labels, SOAP completeness, vitals consistency, and ICD-10 presence are validated on every record.</span></div></div>
            </Card>
          ) : isSupport ? (
            <Card className="config-card">
              <ConfigHeader number="03" icon={<ShieldCheck />} title="Conversation controls" description="Industry, emotional arc, and turn policy" />
              <div className="field-block">
                <label htmlFor="support-industry">Industry scenario</label>
                <select id="support-industry" className="studio-select" value={config.support.industry} onChange={(event) => setConfig({ ...config, support: { ...config.support, industry: event.target.value as SupportIndustry } })}>
                  <option value="mixed">Mixed services</option><option value="telecom">Telecom</option><option value="ecommerce">E-commerce</option><option value="banking">Banking</option><option value="saas">SaaS</option>
                </select>
              </div>
              <div className="field-block">
                <label htmlFor="sentiment-arc">Sentiment arc</label>
                <select id="sentiment-arc" className="studio-select" value={config.support.sentiment_arc} onChange={(event) => setConfig({ ...config, support: { ...config.support, sentiment_arc: event.target.value as SentimentArc } })}>
                  <option value="recovery">Recovery · frustrated to positive</option><option value="steady-positive">Steady positive</option><option value="escalation">Escalation required</option>
                </select>
              </div>
              <div className="field-block">
                <div className="field-label"><label htmlFor="max-turns">Maximum turns</label><output htmlFor="max-turns">{config.support.max_turns}</output></div>
                <input id="max-turns" type="range" min="4" max="10" step="1" value={config.support.max_turns} onChange={(event) => setConfig({ ...config, support: { ...config.support, max_turns: Number(event.target.value) } })} style={{ "--range-progress": `${((config.support.max_turns - 4) / 6) * 100}%` } as React.CSSProperties} />
                <div className="range-marks"><span>4</span><span>6</span><span>8</span><span>10</span></div>
              </div>
              <div className="clinical-policy"><ShieldCheck aria-hidden="true" /><div><strong>Conversation policy enforced</strong><span>Pseudonymous customer IDs, alternating roles, coherent resolution state, and sentiment progression are validated on every record.</span></div></div>
            </Card>
          ) : isLegal ? (
            <Card className="config-card">
              <ConfigHeader number="03" icon={<ShieldCheck />} title="Contract controls" description="Document family and clause budget" />
              <div className="field-block">
                <label htmlFor="legal-document-type">Document type</label>
                <select id="legal-document-type" className="studio-select" value={config.legal.document_type} onChange={(event) => setConfig({ ...config, legal: { ...config.legal, document_type: event.target.value as LegalDocumentType } })}>
                  <option value="mixed">Mixed contracts</option><option value="nda">NDA</option><option value="service-agreement">Service agreement</option><option value="msa">Master services agreement</option>
                </select>
              </div>
              <div className="field-block">
                <div className="field-label"><label htmlFor="max-clauses">Maximum clauses</label><output htmlFor="max-clauses">{config.legal.max_clauses}</output></div>
                <input id="max-clauses" type="range" min="3" max="8" step="1" value={config.legal.max_clauses} onChange={(event) => setConfig({ ...config, legal: { ...config.legal, max_clauses: Number(event.target.value) } })} style={{ "--range-progress": `${((config.legal.max_clauses - 3) / 5) * 100}%` } as React.CSSProperties} />
                <div className="range-marks"><span>3</span><span>5</span><span>6</span><span>8</span></div>
              </div>
              <div className="clinical-policy"><ShieldCheck aria-hidden="true" /><div><strong>Contract policy enforced</strong><span>Synthetic labeling, pseudonymous parties, sequential clauses, confidentiality coverage, and disclaimer presence are validated on every record.</span></div></div>
            </Card>
          ) : isFinance ? (
            <Card className="config-card">
              <ConfigHeader number="03" icon={<ShieldCheck />} title="Statement controls" description="Statement family and line budget" />
              <div className="field-block">
                <label htmlFor="finance-statement-type">Statement type</label>
                <select id="finance-statement-type" className="studio-select" value={config.finance.statement_type} onChange={(event) => setConfig({ ...config, finance: { ...config.finance, statement_type: event.target.value as FinanceStatementType } })}>
                  <option value="mixed">Mixed statements</option><option value="balance-sheet">Balance sheet</option><option value="income-statement">Income statement</option><option value="cash-flow">Cash flow</option>
                </select>
              </div>
              <div className="field-block">
                <div className="field-label"><label htmlFor="max-lines">Maximum line items</label><output htmlFor="max-lines">{config.finance.max_lines}</output></div>
                <input id="max-lines" type="range" min="3" max="8" step="1" value={config.finance.max_lines} onChange={(event) => setConfig({ ...config, finance: { ...config.finance, max_lines: Number(event.target.value) } })} style={{ "--range-progress": `${((config.finance.max_lines - 3) / 5) * 100}%` } as React.CSSProperties} />
                <div className="range-marks"><span>3</span><span>5</span><span>6</span><span>8</span></div>
              </div>
              <div className="clinical-policy"><ShieldCheck aria-hidden="true" /><div><strong>Ledger policy enforced</strong><span>Synthetic entity IDs, valid period windows, debit/credit totals, and net-position integrity are validated on every record.</span></div></div>
            </Card>
          ) : isHr ? (
            <Card className="config-card">
              <ConfigHeader number="03" icon={<ShieldCheck />} title="People controls" description="Document family and section budget" />
              <div className="field-block">
                <label htmlFor="hr-document-type">Document type</label>
                <select id="hr-document-type" className="studio-select" value={config.hr.document_type} onChange={(event) => setConfig({ ...config, hr: { ...config.hr, document_type: event.target.value as HRDocumentType } })}>
                  <option value="mixed">Mixed HR records</option><option value="offer-letter">Offer letter</option><option value="performance-review">Performance review</option><option value="onboarding-checklist">Onboarding checklist</option>
                </select>
              </div>
              <div className="field-block">
                <div className="field-label"><label htmlFor="max-sections">Maximum sections</label><output htmlFor="max-sections">{config.hr.max_sections}</output></div>
                <input id="max-sections" type="range" min="3" max="6" step="1" value={config.hr.max_sections} onChange={(event) => setConfig({ ...config, hr: { ...config.hr, max_sections: Number(event.target.value) } })} style={{ "--range-progress": `${((config.hr.max_sections - 3) / 3) * 100}%` } as React.CSSProperties} />
                <div className="range-marks"><span>3</span><span>4</span><span>5</span><span>6</span></div>
              </div>
              <div className="clinical-policy"><ShieldCheck aria-hidden="true" /><div><strong>People policy enforced</strong><span>Pseudonymous employee IDs, positive CTC, sequential sections, and synthetic disclaimers are validated on every record.</span></div></div>
            </Card>
          ) : isRetail ? (
            <Card className="config-card">
              <ConfigHeader number="03" icon={<ShieldCheck />} title="Catalog controls" description="Category mix and review depth" />
              <div className="field-block">
                <label htmlFor="retail-category">Product category</label>
                <select id="retail-category" className="studio-select" value={config.retail.category} onChange={(event) => setConfig({ ...config, retail: { ...config.retail, category: event.target.value as RetailCategory } })}>
                  <option value="mixed">Mixed catalog</option><option value="electronics">Electronics</option><option value="home">Home</option><option value="apparel">Apparel</option><option value="grocery">Grocery</option>
                </select>
              </div>
              <div className="field-block">
                <div className="field-label"><label htmlFor="max-reviews">Maximum reviews</label><output htmlFor="max-reviews">{config.retail.max_reviews}</output></div>
                <input id="max-reviews" type="range" min="1" max="5" step="1" value={config.retail.max_reviews} onChange={(event) => setConfig({ ...config, retail: { ...config.retail, max_reviews: Number(event.target.value) } })} style={{ "--range-progress": `${((config.retail.max_reviews - 1) / 4) * 100}%` } as React.CSSProperties} />
                <div className="range-marks"><span>1</span><span>2</span><span>3</span><span>5</span></div>
              </div>
              <div className="clinical-policy"><ShieldCheck aria-hidden="true" /><div><strong>Catalog policy enforced</strong><span>Synthetic SKUs, list/sale pricing integrity, sequential reviews, and rating averages are validated on every record.</span></div></div>
            </Card>
          ) : (
            <Card className="config-card">
              <ConfigHeader number="03" icon={<WandSparkles />} title="Render & degradation" description="Control document realism" />
              <div className="toggle-list">
                <Toggle label="Render document images" detail="Create PDF and PNG outputs" checked={config.render} onChange={(render) => setConfig({ ...config, render })} />
                <Toggle label="Apply scan degradation" detail="Simulate real capture conditions" checked={config.degrade} onChange={(degrade) => setConfig({ ...config, degrade })} />
              </div>
              <div className={cn("degradation-grid", !config.degrade && "control-disabled")} aria-disabled={!config.degrade}>
                {(["noise", "blur", "perspective", "stamps"] as const).map((key) => <MiniSlider key={key} label={key} value={config.degradation[key]} onChange={(value) => updateDegradation(key, value)} disabled={!config.degrade} />)}
              </div>
              <div className="advanced-block">
                <button type="button" aria-expanded={advancedOpen} onClick={() => setAdvancedOpen(!advancedOpen)}><FileJson2 aria-hidden="true" /><span><strong>Advanced JSON</strong><small>Fine-tune degradation parameters</small></span><ChevronDown className={advancedOpen ? "rotate-180" : ""} aria-hidden="true" /></button>
                {advancedOpen ? <div className="json-editor"><div><span>degradation.json</span><Badge>JSON</Badge></div><textarea aria-label="Advanced degradation JSON" value={advancedJson} onChange={(event) => setAdvancedJson(event.target.value)} aria-invalid={Boolean(jsonError)} />{jsonError ? <p role="alert">{jsonError}</p> : null}</div> : null}
              </div>
            </Card>
          )}
        </div>

        <aside className="run-column" aria-label="Generation run summary">
          <Card className="run-card">
            <div className="run-card-head"><div><p className="eyebrow">RUN MANIFEST</p><h2>Ready to forge</h2></div><span className="status-lamp" /></div>
            <dl className="run-manifest">
              <div><dt>Domain</dt><dd>{meta.label}</dd></div><div><dt>Records</dt><dd>{config.count}</dd></div><div><dt>Language</dt><dd>{config.language}</dd></div><div><dt>Provider</dt><dd>{config.provider === "nemo" ? "NVIDIA NeMo" : "Offline forge"}</dd></div><div><dt>Seed</dt><dd>{config.seed}</dd></div><div><dt>Outputs</dt><dd>{isStructured ? "JSON · JSONL" : config.render ? "JSON · PDF · PNG" : "JSON"}</dd></div>
            </dl>
            <div className="estimated-row"><span>Estimated runtime</span><strong>~{Math.max(3, Math.ceil(config.count * (config.provider === "nemo" ? 0.42 : 0.18)))}s</strong></div>
            <Button className="button-primary button-generate" loading={submitting} onClick={generate}><Sparkles aria-hidden="true" /> {submitting ? "Starting job" : "Generate dataset"}</Button>
            <button className="reset-button" onClick={reset}>Reset configuration</button>
          </Card>
          <div className="schema-note"><ShieldCheck aria-hidden="true" /><div><strong>Validation first</strong><span>{isHealthcare ? "Synthetic labeling, pseudonymous identity, SOAP completeness, ICD-10 presence, and vital-sign consistency are checked before output." : isSupport ? "Synthetic labeling, pseudonymous identity, role alternation, resolution state, and sentiment progression are checked before output." : "GST arithmetic, date logic, addresses, currencies, and line-item integrity are checked before output."}</span></div></div>
        </aside>
      </div>

      {job ? <section className="job-section" aria-live="polite">
        <Card className="job-progress-card">
          <div className="job-progress-head"><div><span className={cn("job-state-icon", job.status === "completed" && "job-complete")}>{job.status === "completed" ? <Check /> : <LoaderCircle className={job.status !== "failed" ? "animate-spin" : ""} />}</span><div><p className="eyebrow">JOB {job.id}</p><h2>{job.status === "completed" ? "Dataset forged successfully" : job.status === "failed" ? "Generation failed" : "Generation in progress"}</h2><span>{job.message ?? (job.status === "completed" ? `${job.results.length} ${meta.noun} passed validation` : "Waiting for worker telemetry")}</span></div></div><strong>{job.progress}%</strong></div>
          <div className="progress-track"><span style={{ width: `${job.progress}%` }} /></div>
        </Card>
        {activeResult ? <div className="result-grid"><Card className="result-preview-card"><div className="result-card-head"><div><p className="eyebrow">OUTPUT PREVIEW</p><h3>{activeResult.title}</h3></div><Badge tone="accent">VALIDATED</Badge></div><DocumentPreview document={activeResult} compact /></Card><Card className="result-validation-card"><div className="score-ring" style={{ "--score": `${activeResult.validationScore * 3.6}deg` } as React.CSSProperties}><div><strong>{activeResult.validationScore}</strong><span>/ 100</span></div></div><div><p className="eyebrow">QUALITY SCORE</p><h3>Validation checks</h3></div><ValidationRules document={activeResult} /><div className="result-actions"><Link href="/gallery" className="button"><Eye aria-hidden="true" /> Inspect results</Link><button className="button" onClick={() => downloadManifest(activeResult)}><Download aria-hidden="true" /> Manifest</button></div></Card></div> : null}
      </section> : null}
    </div>
  );
}

function ConfigHeader({ number, icon, title, description }: { number: string; icon: React.ReactNode; title: string; description: string }) {
  return <div className="config-header"><span>{number}</span><div className="config-icon">{icon}</div><div><h2>{title}</h2><p>{description}</p></div></div>;
}

function Toggle({ label, detail, checked, onChange }: { label: string; detail: string; checked: boolean; onChange: (value: boolean) => void }) {
  return <div className="toggle-row"><div><strong>{label}</strong><span>{detail}</span></div><button type="button" role="switch" aria-checked={checked} className={checked ? "toggle-on" : ""} onClick={() => onChange(!checked)}><span /></button></div>;
}

function MiniSlider({ label, value, onChange, disabled }: { label: string; value: number; onChange: (value: number) => void; disabled: boolean }) {
  return <div className="mini-slider"><div><label htmlFor={`degrade-${label}`}>{label}</label><output>{Math.round(value * 100)}%</output></div><input id={`degrade-${label}`} disabled={disabled} type="range" min="0" max="1" step="0.01" value={value} onChange={(event) => onChange(Number(event.target.value))} style={{ "--range-progress": `${value * 100}%` } as React.CSSProperties} /></div>;
}

function downloadManifest(document: typeof fallbackGallery[number]) {
  const blob = new Blob([JSON.stringify(document, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = window.document.createElement("a");
  link.href = url;
  link.download = `${document.id}.json`;
  link.click();
  URL.revokeObjectURL(url);
}
