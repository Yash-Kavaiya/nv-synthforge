# API integration contract

The FastAPI OpenAPI document served at `/docs` (schema at `/openapi.json`) is authoritative for a running revision. This page records the routes and request shape consumed by the current Next.js client so frontend/backend drift is visible during review.

## Base URL

Browser code reads `NEXT_PUBLIC_API_URL` and defaults to `http://localhost:8000`. The value is public configuration and is normally embedded during `next build`; it must never contain a credential.

All application routes currently use the `/api/v1` prefix.

## Client route inventory

| Method | Path | Client use |
| --- | --- | --- |
| `GET` | `/api/v1/health` | API availability and service metadata |
| `GET` | `/api/v1/domains` | Domain registry and capability state |
| `GET` | `/api/v1/gallery` | Recent/generated document metadata |
| `POST` | `/api/v1/generate` | Start an invoice generation job |
| `GET` | `/api/v1/jobs/{job_id}` | Poll generation status and results |
| `WS` | `/api/v1/jobs/{job_id}/ws` | Optional job update channel exposed by the client helper |
| `GET` | `/api/v1/benchmarks` | List deterministic benchmark summaries for completed jobs |
| `POST` | `/api/v1/benchmarks` | Run the deterministic validation benchmark for a completed job |

A route appearing here means the frontend calls or constructs it; it is not evidence that every deployed revision implements it. Compare this list with `/openapi.json` and run the smoke test before a demo.

## Generation request used by the UI

The Invoice Studio sends JSON with this shape:

```json
{
  "domain": "invoices",
  "count": 25,
  "seed": 260713,
  "provider": "offline",
  "language": "en-IN",
  "render": true,
  "degrade": true,
  "degradation": {
    "noise": 0.18,
    "blur": 0.08,
    "perspective": 0.12,
    "stamps": 0.24
  }
}
```

Current server values are:

- `domain`: `invoices`/`invoice` for GST documents, or `healthcare` for synthetic clinical notes;
- `provider`: `offline` for every available domain, or `nemo` for invoices when configured;
- `language`: `en-IN`, `hi-IN`, or `gu-IN`;
- `count`: constrained to 1–100;
- degradation controls: invoice-only numbers from 0 through 1.

The healthcare path currently exports validated JSON and JSONL records; `render` and `degrade` are invoice artifact controls. The server remains responsible for authoritative validation. The `nemo` provider is optional and requires compatible backend dependencies, outbound access, and server-side `NVIDIA_API_KEY` configuration.

## Job and document fields consumed by the UI

The frontend normalizes minor naming differences, but its canonical job model contains:

- `id`;
- `status`: `queued`, `running`, `completed`, or `failed`;
- `progress`: 0–100;
- optional `message` and `createdAt`;
- `results`: document metadata.

Document metadata consumed by the gallery includes an identifier, title, domain, language, provider, creation time, validation score/status, optional invoice summary fields, optional PDF/image/JSON URLs, and validation-rule results. Consult the live OpenAPI schema for the exact wire names rather than treating the frontend normalizer as a server specification.

## Error and fallback behavior

The browser client applies an eight-second request timeout and treats non-2xx responses as errors. If generation cannot reach the backend, the current Studio can run a clearly labelled client-side demonstration simulation. Simulation output and bundled gallery/dashboard fixtures are presentation data, not API-generated artifacts or measured production metrics.

Provider failures must be explicit. A failed NeMo request must not silently relabel offline output as NeMo-generated.

## Smoke test

With both services running:

```bash
make smoke
```

For deployed services:

```bash
API_URL=https://api.example.test \
WEB_URL=https://app.example.test \
make smoke
```

The lightweight script checks the health route, domain registry, and frontend over HTTP. To exercise the full offline pipeline, run `make e2e-smoke`; it creates two deterministic invoices, verifies rendered/degraded/export artifacts, checks gallery persistence, downloads an image, and runs the deterministic benchmark. Neither smoke path calls the optional NeMo provider.
