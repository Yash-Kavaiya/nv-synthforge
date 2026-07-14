# Track C: Synthetic Data Generation — NV-SynthForge pitch

**Event:** OpenHackathons · Track C: SDG (Synthetic Data Generation)  
**Project:** [NV-SynthForge](https://github.com/Yash-Kavaiya/nv-synthforge)  
**Core idea:** A reproducible SDG pipeline that produces **paired training/eval packs** (JSON ground truth + PDF/image documents), then a website where users score **OCR / document-AI models** on structure accuracy.

## Why this fits Track C

Track C asks for pipelines that generate **high-quality training data** (e.g. synthetic multilingual conversation datasets). NV-SynthForge does that **and** closes the loop with evaluation:

1. **Generate** multi-domain synthetic data offline (and optionally via NVIDIA NeMo Data Designer).
2. **Render** document artifacts (HTML/PDF/PNG + degraded scans for invoices).
3. **Export** JSON/JSONL/CSV + Hugging Face-style dataset cards.
4. **Evaluate** OCR model output against the synthetic JSON structure.

The OCR harness is not a random UI gimmick — it is the reason the synthetic documents are useful: **you cannot train or rank OCR models without labeled structure**.

## Mapping the team diagram

| Diagram box | NV-SynthForge status |
| --- | --- |
| HuggingFace dataset / sample data / empty + one prompt | Studio seed/count/language controls; HF dataset card export; optional NeMo path |
| NeMo Curator / Data Designer / Synthesiser | Optional NeMo Data Designer adapter (`NVIDIA_API_KEY`); offline generators are the default |
| Create JSON data | Implemented for 7 domains |
| Create PDF | Implemented for invoices (ReportLab baseline + optional WeasyPrint) |
| Agent harness / `.tex` templates | Roadmap / demo extension (LaTeX path can reuse invoice schema) |
| Separate UI: user model → eval OCR via JSON + PDF structure | **Implemented** at `/ocr` + `POST /api/v1/ocr/evaluate` |

## Demo script (5 minutes)

### One-command launcher (recommended)

**Git Bash / MSYS:**

```bash
cd C:/Users/yashk/nv-synthforge
bash scripts/demo-track-c.sh
```

**PowerShell:**

```powershell
cd C:\Users\yashk\nv-synthforge
powershell -ExecutionPolicy Bypass -File scripts\demo-track-c.ps1
```

The launcher picks the first free backend port among `8000/8001/8002`, starts the frontend on `3000` with rewrites pointed at that backend, and prints demo URLs.

### Smoke the OCR harness

With the backend running:

```bash
python scripts/ocr-demo-smoke.py
# or pin a base:
API_BASE=http://127.0.0.1:8001 python scripts/ocr-demo-smoke.py
```

### Manual walkthrough

1. Open http://localhost:3000/studio?domain=invoices  
2. Generate with **render + degrade** enabled (seed fixed for reproducibility).  
3. Open Gallery → download JSON + PDF/degraded image.  
4. Open http://localhost:3000/ocr  
5. Select the invoice sample → **Run noisy demo OCR** *or* paste your model JSON.  
6. Show field-level accuracy (identity / parties / amounts / line items).  
7. Mention other SDG domains: healthcare, support (multilingual conversations), legal, finance, HR, retail.

## API surface for OCR eval

```http
GET  /api/v1/ocr/samples
POST /api/v1/ocr/evaluate
```

Body examples:

```json
{
  "job_id": "<completed-invoice-job>",
  "document_index": 0,
  "model_name": "my-ocr-v1",
  "prediction": { "invoice_number": "...", "seller": { "...": "..." } }
}
```

Or synthetic noisy model:

```json
{
  "job_id": "<completed-invoice-job>",
  "document_index": 0,
  "demo_noise": 0.25,
  "model_name": "synthetic-ocr-demo"
}
```

## Judging talking points

- **Quality:** deterministic validators (GST arithmetic, SOAP, conversation arcs, etc.).
- **Reproducibility:** seeds, offline default, artifact persistence.
- **NVIDIA alignment:** optional NeMo Data Designer path; offline fallback when credentials unavailable.
- **Multilingual:** en-IN / hi-IN / gu-IN labels on generators and support conversations.
- **End-to-end product:** generation studio + gallery + quality benchmarks + OCR structure eval website.

## Honest limits (say these)

- OCR eval currently scores **invoice JSON structure**, not pixel-level OCR model hosting.
- Users bring model output (JSON); we do not run arbitrary GPU models in-browser.
- NeMo path is optional and environment-dependent.
- Auth, multi-tenant SaaS, and production billing are out of MVP scope.

## Stretch goals if time remains

- Upload prediction file (`.json`) drag-and-drop.
- Score from free-text OCR by running a lightweight field extractor.
- Expand structure eval to legal contracts and finance statements.
- Publish a public HF dataset of degraded invoice scans + labels.
