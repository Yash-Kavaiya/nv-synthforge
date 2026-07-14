"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Crosshair, FileJson, Play, RefreshCw, ScanSearch, Sparkles, Upload } from "lucide-react";
import { api, resolveApiAssetUrl } from "@/lib/api";
import type { OCREvalReport, OCRSample } from "@/lib/types";
import { Badge, Button, Card, Skeleton } from "./ui";

const DEMO_PREDICTION = `{
  "invoice_number": "paste-your-model-output-here",
  "invoice_date": "2026-01-01",
  "currency": "INR",
  "seller": { "name": "", "gstin": "", "address": { "line1": "", "city": "", "state": "", "state_code": "", "postal_code": "" } },
  "buyer": { "name": "", "gstin": "", "address": { "line1": "", "city": "", "state": "", "state_code": "", "postal_code": "" } },
  "items": [],
  "subtotal": "0.00",
  "cgst": "0.00",
  "sgst": "0.00",
  "igst": "0.00",
  "grand_total": "0.00"
}`;

export function OCRBenchClient() {
  const [samples, setSamples] = useState<OCRSample[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [modelName, setModelName] = useState("user-ocr-model");
  const [predictionText, setPredictionText] = useState(DEMO_PREDICTION);
  const [report, setReport] = useState<OCREvalReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [demoNoise, setDemoNoise] = useState(0.25);

  const loadSamples = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const remote = await api.ocrSamples();
      setSamples(remote);
      if (remote[0]) {
        setSelected(`${remote[0].jobId}:${remote[0].documentIndex}`);
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load OCR samples");
      setSamples([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadSamples(), 0);
    return () => window.clearTimeout(timer);
  }, [loadSamples]);

  const activeSample = useMemo(() => {
    return samples.find((sample) => `${sample.jobId}:${sample.documentIndex}` === selected) ?? null;
  }, [samples, selected]);

  async function ensureInvoiceSample() {
    setRunning(true);
    setError(null);
    try {
      const job = await api.generate({
        domain: "invoices",
        count: 1,
        seed: 4242,
        provider: "offline",
        language: "en-IN",
        render: true,
        degrade: true,
        degradation: { noise: 0.2, blur: 0.1, perspective: 0.1, stamps: 0.15 },
        healthcare: { clinical_profile: "mixed", include_medications: true },
        support: { industry: "mixed", sentiment_arc: "recovery", max_turns: 6 },
        legal: { document_type: "mixed", max_clauses: 6 },
        finance: { statement_type: "mixed", max_lines: 6 },
        hr: { document_type: "mixed", max_sections: 4 },
        retail: { category: "mixed", max_reviews: 3 },
      });
      // poll briefly
      let current = job;
      for (let i = 0; i < 40; i += 1) {
        if (current.status === "completed" || current.status === "failed") break;
        await new Promise((resolve) => setTimeout(resolve, 250));
        current = await api.job(job.id);
      }
      if (current.status !== "completed") {
        throw new Error("Invoice generation did not complete");
      }
      await loadSamples();
      setSelected(`${current.id}:0`);
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "Unable to generate invoice sample");
    } finally {
      setRunning(false);
    }
  }

  async function runEval(mode: "prediction" | "demo") {
    if (!activeSample && mode === "demo") {
      setError("Generate or select an invoice sample first");
      return;
    }
    setRunning(true);
    setError(null);
    try {
      let payload: Record<string, unknown>;
      if (mode === "demo") {
        payload = {
          job_id: activeSample!.jobId,
          document_index: activeSample!.documentIndex,
          model_name: "synthetic-ocr-demo",
          demo_noise: demoNoise,
        };
      } else {
        const prediction = JSON.parse(predictionText) as Record<string, unknown>;
        payload = {
          job_id: activeSample?.jobId,
          document_index: activeSample?.documentIndex ?? 0,
          model_name: modelName,
          prediction,
        };
      }
      const result = await api.ocrEvaluate(payload);
      setReport(result);
      setPredictionText(JSON.stringify(result.prediction, null, 2));
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "OCR evaluation failed");
    } finally {
      setRunning(false);
    }
  }

  const pdfUrl = activeSample?.fileUrls.pdf ? resolveApiAssetUrl(activeSample.fileUrls.pdf) : undefined;
  const imageUrl = activeSample?.fileUrls.png
    ? resolveApiAssetUrl(activeSample.fileUrls.png)
    : activeSample?.fileUrls["degraded-image"]
      ? resolveApiAssetUrl(activeSample.fileUrls["degraded-image"])
      : undefined;

  return (
    <div className="page-stack ocr-page">
      <header className="route-header">
        <div>
          <p className="eyebrow">TRACK C · SDG + OCR HARNESS</p>
          <h1>OCR Structure Benchmark</h1>
          <p>
            Generate synthetic invoices with paired JSON ground truth and PDF/image artifacts, then score any model&apos;s extracted JSON against the structure.
          </p>
        </div>
        <div className="route-header-actions">
          <Button onClick={() => void loadSamples()} disabled={loading || running}><RefreshCw className={loading ? "animate-spin" : ""} aria-hidden="true" /> Refresh samples</Button>
          <Button onClick={() => void ensureInvoiceSample()} disabled={running}><Sparkles aria-hidden="true" /> Generate invoice pack</Button>
        </div>
      </header>

      {error ? <div className="notice notice-error" role="alert"><strong>Evaluation error</strong><span>{error}</span></div> : null}

      <div className="ocr-grid">
        <Card className="config-card">
          <div className="config-header">
            <span>01</span>
            <div>
              <h2>Ground-truth sample</h2>
              <p>Synthetic invoice JSON + optional PDF/image from the SDG pipeline</p>
            </div>
          </div>
          {loading ? <Skeleton className="gallery-skeleton" /> : (
            <div className="field-block">
              <label htmlFor="ocr-sample">Invoice sample</label>
              <select id="ocr-sample" className="studio-select" value={selected} onChange={(event) => setSelected(event.target.value)}>
                {samples.length === 0 ? <option value="">No invoice samples yet</option> : null}
                {samples.map((sample) => (
                  <option key={`${sample.jobId}:${sample.documentIndex}`} value={`${sample.jobId}:${sample.documentIndex}`}>
                    {sample.title} · {sample.invoiceNumber} · ₹{sample.grandTotal}
                  </option>
                ))}
              </select>
            </div>
          )}
          {activeSample ? (
            <div className="ocr-sample-meta">
              <div><small>JOB</small><strong>{activeSample.jobId}</strong></div>
              <div><small>INVOICE</small><strong>{activeSample.invoiceNumber}</strong></div>
              <div><small>TOTAL</small><strong>₹{activeSample.grandTotal}</strong></div>
              <div><small>SCORE</small><strong>{activeSample.validationScore ?? "—"}</strong></div>
            </div>
          ) : null}
          <div className="ocr-artifact-links">
            {pdfUrl ? <a className="button button-secondary" href={pdfUrl} target="_blank" rel="noreferrer">Open PDF</a> : null}
            {imageUrl ? <a className="button button-secondary" href={imageUrl} target="_blank" rel="noreferrer">Open image</a> : null}
            <Link className="button button-secondary" href="/studio?domain=invoices">Open Studio</Link>
          </div>
        </Card>

        <Card className="config-card">
          <div className="config-header">
            <span>02</span>
            <div>
              <h2>Model prediction</h2>
              <p>Paste OCR/document-AI JSON, or run a synthetic noisy demo model</p>
            </div>
          </div>
          <div className="field-block">
            <label htmlFor="model-name">Model name</label>
            <input id="model-name" className="studio-input" value={modelName} onChange={(event) => setModelName(event.target.value)} />
          </div>
          <div className="field-block">
            <div className="field-label"><label htmlFor="demo-noise">Demo OCR noise</label><output htmlFor="demo-noise">{demoNoise.toFixed(2)}</output></div>
            <input id="demo-noise" type="range" min="0.05" max="0.6" step="0.05" value={demoNoise} onChange={(event) => setDemoNoise(Number(event.target.value))} />
          </div>
          <div className="field-block">
            <label htmlFor="prediction-json">Prediction JSON</label>
            <textarea id="prediction-json" className="ocr-json" rows={16} value={predictionText} onChange={(event) => setPredictionText(event.target.value)} spellCheck={false} />
          </div>
          <div className="ocr-actions">
            <Button onClick={() => void runEval("prediction")} disabled={running || !activeSample}><Upload aria-hidden="true" /> Score pasted JSON</Button>
            <Button onClick={() => void runEval("demo")} disabled={running || !activeSample}><Play aria-hidden="true" /> Run noisy demo OCR</Button>
          </div>
        </Card>
      </div>

      {report ? (
        <Card className="ocr-report">
          <div className="route-header compact">
            <div>
              <p className="eyebrow">FIELD-LEVEL STRUCTURE SCORE</p>
              <h2>{report.model} · {report.accuracy.toFixed(2)}%</h2>
              <p>{report.correctFields}/{report.totalFields} fields matched · {report.metricScope}</p>
            </div>
            <Badge tone="accent"><ScanSearch aria-hidden="true" /> OCR EVAL</Badge>
          </div>
          <div className="ocr-group-grid">
            {Object.entries(report.groups).map(([name, group]) => (
              <article key={name}>
                <small>{name}</small>
                <strong>{group.accuracy.toFixed(1)}%</strong>
                <span>{group.correct}/{group.total} fields</span>
              </article>
            ))}
          </div>
          <div className="ocr-compare-table-wrap">
            <table className="ocr-compare-table">
              <thead>
                <tr>
                  <th>Field</th>
                  <th>Group</th>
                  <th>Expected</th>
                  <th>Predicted</th>
                  <th>Match</th>
                </tr>
              </thead>
              <tbody>
                {report.comparisons.map((row) => (
                  <tr key={row.field} className={row.matched ? "match" : "miss"}>
                    <td>{row.field}</td>
                    <td>{row.group}</td>
                    <td>{row.expected ?? "—"}</td>
                    <td>{row.predicted ?? "—"}</td>
                    <td>{row.matched ? "✓" : "✗"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : (
        <Card className="ocr-empty">
          <FileJson aria-hidden="true" />
          <div>
            <strong>No evaluation yet</strong>
            <span>Generate a synthetic invoice pack, paste model JSON (or run the noisy demo), and score structure accuracy against ground truth.</span>
          </div>
          <Crosshair aria-hidden="true" />
        </Card>
      )}
    </div>
  );
}
