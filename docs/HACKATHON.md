# Hackathon Submission

## Submission narrative

### One-line pitch

NV-SynthForge turns a domain schema into reproducible synthetic datasets through a local-first interface, with an optional NVIDIA NeMo Data Designer path when credentials and dependencies are available.

### Problem

Teams need realistic test data before production data is available or safe to share. Existing approaches often force a choice between brittle hand-written fixtures and opaque hosted generation. They also make it easy to confuse a catalog of promised domains with generators that actually work.

### Solution

NV-SynthForge provides a FastAPI generation service and Next.js workspace with explicit capability states. The MVP implements the invoice path, keeps additional domains visible as registry cards, and defaults to deterministic offline generation. An optional adapter demonstrates how NVIDIA NeMo Data Designer can extend generation without making the credentialed path a prerequisite for local evaluation.

### Why it matters

- **Demoable without secrets:** judges can exercise the baseline path locally.
- **Reproducible:** seed-driven generation supports debugging and regression tests where exposed by the current API.
- **Honest capability discovery:** registry metadata distinguishes implemented generators from roadmap domains.
- **Extensible:** provider adapters and domain boundaries allow generators to evolve independently.
- **Production-aware:** CI, container orchestration, security guidance, and deployment notes document the gap between an MVP and an operated service.

### NVIDIA integration

The NeMo route is optional and should only be shown when a compatible `data-designer` package, network access, and `NVIDIA_API_KEY` are available. If those prerequisites are unavailable during judging, demonstrate offline generation and explain the adapter boundary. Do not imply that offline output was produced by NeMo.

### What is working versus next

| Working MVP focus | Environment-dependent | Roadmap / not claimed |
| --- | --- | --- |
| Invoice generation, GST validation, and quality scoring | NeMo Data Designer network generation | Generators for registry-only domains |
| HTML/PDF/PNG rendering and configurable degradation | WeasyPrint-enhanced PDF fidelity | Managed durable object storage |
| JSON/JSONL/CSV/HF-style exports and optional Parquet | Container/runtime font differences | Authentication and multi-tenancy |
| Background jobs, WebSocket status, SQLite gallery | External API availability | OCR/VLM model integrations |
| Deterministic validation benchmark | Cloud Run deployment until smoke-tested | Hosted quotas, sharing, and billing |

## Demo script (about 4 minutes)

### 0:00-0:30 — Set context

> "Product teams need useful test records before they can safely access production data. NV-SynthForge gives them a reproducible local path first, then an optional NeMo-powered path when the environment supports it."

Show the domain registry. Point out that capability state is explicit: invoice is the MVP generation path; other cards are discoverable roadmap entries.

### 0:30-1:45 — Generate invoices offline

1. Select the invoice domain.
2. Keep the provider/mode on the offline default.
3. Choose a small record count and an explicit seed if those controls are exposed in the current UI.
4. Start generation.
5. Show the completed job, quality rules, rendered/degraded image preview, and export links.
6. Open Results Gallery and the deterministic Benchmark page.

Say:

> "This path is deterministic and requires no NVIDIA key, which makes the project reproducible for local development and CI."

Only describe controls and output formats actually visible in the running build.

### 1:45-2:30 — Prove reproducibility and boundaries

Repeat the same request with the same seed if the UI/API exposes it, then compare the supported deterministic fields or artifact checksum. If no comparison view exists, use the API response or tests rather than claiming visual proof.

Open a registry-only domain and show its unavailable/planned state. Emphasize that the catalog does not pretend every card is implemented.

### 2:30-3:15 — Explain the NVIDIA path

If the environment is configured, select the NeMo provider and run a small request. Before the demo, verify:

- `data-designer` imports in the backend environment;
- `NVIDIA_API_KEY` is provided server-side;
- outbound API access works;
- the selected API/model configuration is supported.

If any check fails, do not attempt a live call. Show the adapter in the architecture diagram and say:

> "NeMo is an optional provider behind the same orchestration boundary. Today's live environment is using the deterministic fallback; no NeMo-generated result is being claimed."

### 3:15-3:45 — Architecture and production story

Show `docs/ARCHITECTURE.md` and briefly trace UI → API → provider → artifacts. Mention that local artifacts are persisted by Compose, while Cloud Run needs durable object storage because its filesystem is ephemeral.

### 3:45-4:00 — Close

> "NV-SynthForge delivers the useful baseline now—invoices, reproducibility, and transparent capability states—while leaving a clean path to NeMo-backed and multi-domain generation."

## Pre-demo checklist

- [ ] Run backend tests and frontend lint/build.
- [ ] Start from a clean `.env` with offline mode available.
- [ ] Generate one small invoice artifact and verify it opens.
- [ ] Confirm the UI labels registry-only domains correctly.
- [ ] Verify the exact output formats visible in this build.
- [ ] If showing NeMo, test the package import and API call immediately before presenting.
- [ ] If showing native rendering, test its OS libraries and fonts on the presentation machine.
- [ ] Keep a recorded offline-path backup; do not rely on external APIs for the core demo.

## Suggested submission fields

**Project name:** NV-SynthForge  
**Category:** Developer tools / synthetic data / generative AI  
**Repository:** Add the final public repository URL only after it exists.  
**Try it:** Add the deployed URL only after deployment and smoke testing.  
**Built with:** FastAPI, Python, Next.js, TypeScript; optional NVIDIA NeMo Data Designer integration.
