from __future__ import annotations

from pathlib import Path

path = Path(r"C:/Users/yashk/nv-synthforge/frontend/src/components/studio-client.tsx")
text = path.read_text(encoding="utf-8")

text = text.replace(
    'import type { ClinicalProfile, DomainId, GenerateRequest, Job, Language, Provider, SentimentArc, SupportIndustry } from "@/lib/types";',
    'import type { ClinicalProfile, DomainId, GenerateRequest, Job, Language, LegalDocumentType, Provider, SentimentArc, SupportIndustry } from "@/lib/types";',
)

old_defaults = """const invoiceDefaults: GenerateRequest = {
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
};

function defaultsFor(domain: DomainId): GenerateRequest {
  const shared = {
    ...invoiceDefaults,
    domain,
    degradation: { ...invoiceDefaults.degradation },
    healthcare: { ...invoiceDefaults.healthcare },
    support: { ...invoiceDefaults.support },
  };
  return domain === "invoices"
    ? shared
    : { ...shared, count: 10, render: false, degrade: false };
}
"""

new_defaults = """const invoiceDefaults: GenerateRequest = {
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
};

function defaultsFor(domain: DomainId): GenerateRequest {
  const shared = {
    ...invoiceDefaults,
    domain,
    degradation: { ...invoiceDefaults.degradation },
    healthcare: { ...invoiceDefaults.healthcare },
    support: { ...invoiceDefaults.support },
    legal: { ...invoiceDefaults.legal },
  };
  return domain === "invoices"
    ? shared
    : { ...shared, count: 10, render: false, degrade: false };
}
"""

if old_defaults not in text:
    raise SystemExit("defaults block missing")
text = text.replace(old_defaults, new_defaults, 1)

text = text.replace(
    'message: progress >= 100 ? `${request.count} synthetic ${request.domain === "invoices" ? "invoices validated" : request.domain === "healthcare" ? "clinical notes forged" : "conversations synthesized"}` : progress > 68 ? "Running schema and validation checks" : "Rendering document variants",',
    'message: progress >= 100 ? `${request.count} synthetic ${request.domain === "invoices" ? "invoices validated" : request.domain === "healthcare" ? "clinical notes forged" : request.domain === "legal" ? "contracts drafted" : "conversations synthesized"}` : progress > 68 ? "Running schema and validation checks" : "Rendering document variants",',
)

old_flags = """  const isHealthcare = config.domain === "healthcare";
  const isSupport = config.domain === "support";
  const isStructured = isHealthcare || isSupport;
  const workbenchLabel = isHealthcare ? "HEALTHCARE WORKBENCH / V1.0" : isSupport ? "SUPPORT WORKBENCH / V1.0" : "INVOICE WORKBENCH / V1.4";
  const studioTitle = isHealthcare ? "Clinical Note Studio" : isSupport ? "Conversation Studio" : "Invoice Studio";
  const studioDescription = isHealthcare
    ? "Generate privacy-safe synthetic SOAP notes with pseudonymous identities and clinical validation."
    : isSupport
      ? "Generate deterministic multi-turn service conversations with sentiment and resolution validation."
      : "Compose a reproducible synthetic document run, then inspect every validation signal.";
"""

new_flags = """  const isHealthcare = config.domain === "healthcare";
  const isSupport = config.domain === "support";
  const isLegal = config.domain === "legal";
  const isStructured = isHealthcare || isSupport || isLegal;
  const workbenchLabel = isHealthcare
    ? "HEALTHCARE WORKBENCH / V1.0"
    : isSupport
      ? "SUPPORT WORKBENCH / V1.0"
      : isLegal
        ? "LEGAL WORKBENCH / V1.0"
        : "INVOICE WORKBENCH / V1.4";
  const studioTitle = isHealthcare
    ? "Clinical Note Studio"
    : isSupport
      ? "Conversation Studio"
      : isLegal
        ? "Contract Studio"
        : "Invoice Studio";
  const studioDescription = isHealthcare
    ? "Generate privacy-safe synthetic SOAP notes with pseudonymous identities and clinical validation."
    : isSupport
      ? "Generate deterministic multi-turn service conversations with sentiment and resolution validation."
      : isLegal
        ? "Generate synthetic NDAs, service agreements, and MSAs with clause libraries and risk flags."
        : "Compose a reproducible synthetic document run, then inspect every validation signal.";
"""

if old_flags not in text:
    raise SystemExit("flags block missing")
text = text.replace(old_flags, new_flags, 1)

text = text.replace(
    """            <button type="button" className={isHealthcare ? "segment-active" : ""} aria-pressed={isHealthcare} onClick={() => switchDomain("healthcare")}>Healthcare</button>
            <button type="button" className={isSupport ? "segment-active" : ""} aria-pressed={isSupport} onClick={() => switchDomain("support")}>Support</button>
          </div>
          <div className="studio-header-meta"><Badge tone="accent"><ShieldCheck aria-hidden="true" /> SCHEMA LOCKED</Badge><span>{isHealthcare ? "clinical.soap.v1" : isSupport ? "support.conversation.v1" : "invoice.india.v4"}</span></div>""",
    """            <button type="button" className={isHealthcare ? "segment-active" : ""} aria-pressed={isHealthcare} onClick={() => switchDomain("healthcare")}>Healthcare</button>
            <button type="button" className={isSupport ? "segment-active" : ""} aria-pressed={isSupport} onClick={() => switchDomain("support")}>Support</button>
            <button type="button" className={isLegal ? "segment-active" : ""} aria-pressed={isLegal} onClick={() => switchDomain("legal")}>Legal</button>
          </div>
          <div className="studio-header-meta"><Badge tone="accent"><ShieldCheck aria-hidden="true" /> SCHEMA LOCKED</Badge><span>{isHealthcare ? "clinical.soap.v1" : isSupport ? "support.conversation.v1" : isLegal ? "legal.contract.v1" : "invoice.india.v4"}</span></div>""",
)

text = text.replace(
    '<span>{isHealthcare ? "Clinical adapter calibration pending" : isSupport ? "Conversation adapter calibration pending" : "Higher variation, API-backed"}</span>',
    '<span>{isHealthcare ? "Clinical adapter calibration pending" : isSupport ? "Conversation adapter calibration pending" : isLegal ? "Contract adapter calibration pending" : "Higher variation, API-backed"}</span>',
)

old_controls = """          {isHealthcare ? (
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
          ) : (
"""

new_controls = """          {isHealthcare ? (
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
          ) : (
"""

if old_controls not in text:
    raise SystemExit("controls block missing")
text = text.replace(old_controls, new_controls, 1)

text = text.replace(
    "<div><dt>Domain</dt><dd>{isHealthcare ? \"Healthcare\" : isSupport ? \"Support\" : \"Invoices\"}</dd></div>",
    "<div><dt>Domain</dt><dd>{isHealthcare ? \"Healthcare\" : isSupport ? \"Support\" : isLegal ? \"Legal\" : \"Invoices\"}</dd></div>",
)

text = text.replace(
    "{isHealthcare ? \"Synthetic labeling, pseudonymous identity, SOAP completeness, ICD-10 presence, and vital-sign consistency are checked before output.\" : isSupport ? \"Synthetic labeling, pseudonymous identity, turn alternation, resolution state, and sentiment progression are checked before output.\" : \"GST arithmetic, date logic, addresses, currencies, and line-item integrity are checked before output.\"}",
    "{isHealthcare ? \"Synthetic labeling, pseudonymous identity, SOAP completeness, ICD-10 presence, and vital-sign consistency are checked before output.\" : isSupport ? \"Synthetic labeling, pseudonymous identity, turn alternation, resolution state, and sentiment progression are checked before output.\" : isLegal ? \"Synthetic labeling, distinct parties, sequential clauses, confidentiality, and disclaimer presence are checked before output.\" : \"GST arithmetic, date logic, addresses, currencies, and line-item integrity are checked before output.\"}",
)

text = text.replace(
    "${job.results.length} ${config.domain === \"support\" ? \"conversations\" : config.domain === \"healthcare\" ? \"clinical notes\" : \"invoices\"} passed validation",
    "${job.results.length} ${config.domain === \"support\" ? \"conversations\" : config.domain === \"healthcare\" ? \"clinical notes\" : config.domain === \"legal\" ? \"contracts\" : \"invoices\"} passed validation",
)

path.write_text(text, encoding="utf-8")
print("studio-client updated")
