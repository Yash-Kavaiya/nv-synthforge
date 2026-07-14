# NV-SynthForge

NV-SynthForge is a production-oriented MVP for creating reproducible, multi-domain synthetic datasets through a FastAPI backend and a Next.js interface. It currently generates **seven offline domains**: Indian GST invoices, clinical SOAP notes, customer-support conversations, legal contracts, finance statements, HR records, and retail catalog products — with validation, artifacts, gallery review, and a cross-domain benchmark harness.

The project runs in a deterministic offline mode by default. NVIDIA NeMo Data Designer is an **optional integration** and requires both the compatible `data-designer` Python package and a valid `NVIDIA_API_KEY`. It is not required for the offline path.

> **MVP status:** Interfaces and capabilities are still evolving. Only domains marked implemented below are available for generation.

## Capability matrix

| Capability | MVP status | Requirements / notes |
| --- | --- | --- |
| Invoice domain model, deterministic generator, and quality rules | Implemented | Covers Indian GST invoice records; the running OpenAPI schema is authoritative for request and response fields. |
| Domain registry/catalog | Seven working domains | Invoices, Healthcare, Support, Legal, Finance, HR, and Retail are available end-to-end. |
| Healthcare generation | Implemented as JSON/JSONL | Seeded privacy-safe SOAP notes with pseudonymous patients, plausible vitals, ICD-10 diagnoses, medication data, explicit synthetic disclaimers, and five quality rules. |
| Customer-support conversations | Implemented as JSON/JSONL | Multi-turn chats with industry, sentiment-arc, resolution, sequential timestamps, multilingual labels (en/hi/gu), and five support quality rules. |
| Legal contracts | Implemented as JSON/JSONL | NDAs, service agreements, and MSAs with synthetic parties, clause libraries, risk flags, confidentiality coverage, and five legal quality rules. |
| Finance statements | Implemented as JSON/JSONL | Balance sheets, income statements, and cash-flow records with synthetic entities and reconciled debit/credit totals. |
| HR records | Implemented as JSON/JSONL | Offer letters, performance reviews, and onboarding checklists with pseudonymous employees and sequential sections. |
| Retail catalog products | Implemented as JSON/JSONL | Product listings with SKU, pricing, inventory, and synthetic reviews whose averages reconcile. |
| Deterministic offline generation | Default path | No NVIDIA credential should be needed. Use an explicit seed when the API/UI exposes one. |
| NVIDIA NeMo Data Designer generation | Optional adapter | Requires a compatible `data-designer` installation and `NVIDIA_API_KEY`; availability can vary by environment. |
| API-to-artifact generation flow | Implemented and tested | Background jobs expose REST status plus a WebSocket snapshot; completed jobs persist metadata and artifact references in SQLite. |
| Rendered invoice artifacts | Implemented | HTML, PDF, PNG, and deterministic degraded JPEG outputs are generated. ReportLab provides the portable PDF baseline; the `pdf` extra adds WeasyPrint on supported hosts. |
| Export formats | Implemented with optional Parquet | JSON, JSONL, CSV, and a Hugging Face-compatible dataset card are always written. Parquet is added when the `parquet` extra is installed. |
| Benchmark harness | Implemented deterministic baseline | Cross-domain quality, latency, and throughput for all seven domains. Not an OCR/VLM model host. |
| OCR structure evaluation website | Implemented for invoices | `/ocr` UI + `POST /api/v1/ocr/evaluate` scores user model JSON against synthetic ground truth (identity, parties, amounts, line items). |
| Authentication, tenancy, billing, managed storage | Not implemented | Production hardening items, not MVP claims. |

## Repository layout

```text
backend/                 FastAPI service, generators, and tests
frontend/                Next.js/TypeScript application
docs/                    Architecture, deployment, and demo documentation
.github/_workflows_pending/  CI workflow staged until workflow-scope push is enabled
scripts/                 Infrastructure validation and service smoke tests
artifacts/               Local generated output (ignored by Git)
docker-compose.yml       Local two-service stack
```

## Quickstart

### Prerequisites

- Python 3.11+
- Node.js 20+
- pnpm (Corepack can provide it)
- uv for Python dependency management
- Optional: GNU Make (Git Bash, WSL, or a Windows package manager)
- Optional: Docker Desktop with Compose v2
- Optional NeMo path: compatible `data-designer` package and `NVIDIA_API_KEY`
- Optional native rendering: renderer-specific runtime and system libraries

### Run from source

1. Create local configuration:

   ```bash
   cp .env.example .env
   ```

   On Command Prompt, use `copy .env.example .env`; on PowerShell, use `Copy-Item .env.example .env`.

2. Install dependencies:

   ```bash
   make install
   ```

   Without Make:

   ```bash
   cd backend && uv sync --locked
   cd ../frontend && corepack enable && pnpm install --frozen-lockfile
   ```

3. Start the API and web app in separate terminals:

   ```bash
   make backend-dev
   make frontend-dev
   ```

4. Open:

   - Web UI: <http://localhost:3000>
   - API documentation: <http://localhost:8000/docs>

The browser-facing API URL defaults to `http://localhost:8000`. Keep offline mode for a credential-free demo. Only set `NVIDIA_API_KEY` when exercising the optional NeMo adapter.

### Run with Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

Generated artifacts are bind-mounted to `./artifacts`. Stop the stack with `docker compose down`.

Compose builds `backend/Dockerfile` and `frontend/Dockerfile` explicitly. Native-renderer support inside containers depends on those images including the renderer's system packages.

## Common commands

```bash
make help
make test
make lint
make build
make validate-infra
make smoke                 # lightweight probes after both services are running
make e2e-smoke             # full offline generation/artifact/benchmark exercise
make compose-up
make compose-down
```

GNU Make recipes use `uv` and `pnpm` and work from Git Bash or WSL. The smoke test accepts `API_URL` and `WEB_URL` overrides, for example `API_URL=https://api.example.test WEB_URL=https://app.example.test make smoke`.

## Configuration

See [`.env.example`](.env.example) for local and Compose settings. Secrets belong in `.env` or a managed secret store and must never be committed.

`NEXT_PUBLIC_API_URL` is public browser configuration, not a secret. Next.js generally embeds `NEXT_PUBLIC_*` values at build time; production images must be built with the intended API URL unless the frontend explicitly provides runtime configuration.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API integration contract](docs/API.md)
- [Cloud Run deployment notes](docs/CLOUD_RUN.md)
- [Hackathon submission narrative and demo script](docs/HACKATHON.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)

## Project boundaries

NV-SynthForge is a synthetic-data tool, not a guarantee that generated records are legally, statistically, or operationally suitable for a particular use. Validate schemas, distributions, privacy assumptions, and downstream behavior before using artifacts outside a demonstration or test environment.

## License

Licensed under the [Apache License 2.0](LICENSE).
