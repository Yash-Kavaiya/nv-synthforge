# Contributing to NV-SynthForge

Thank you for improving NV-SynthForge. Keep contributions focused, tested, and honest about capability status—especially the distinction between implemented generators, registry-only domains, optional NeMo behavior, and environment-dependent rendering.

## Development setup

1. Fork or clone the repository.
2. Copy `.env.example` to `.env`.
3. Install Python 3.11+, Node.js 20+, `uv`, and `pnpm` (Corepack can provide pnpm).
4. Run `make install` (or the equivalent commands in the README).
5. Start the services with `make backend-dev` and `make frontend-dev` in separate terminals.

GNU Make is optional. Git Bash and WSL are the simplest Windows environments for the provided recipes. Override `PYTHON=py` when the Windows Python launcher is required.

## Contribution workflow

1. Create a short-lived branch from `main`.
2. Make one coherent change; avoid unrelated formatting churn.
3. Add or update tests for behavior changes.
4. Update documentation when APIs, prerequisites, capability states, or deployment assumptions change.
5. Run the local quality gates:

   ```bash
   make test
   make lint
   make build
   make validate-infra
   ```

6. Open a pull request describing what changed, how it was verified, and any environment-specific limitations.

## Backend guidance

- Keep FastAPI request/response models authoritative and validated.
- Preserve deterministic offline behavior; tests must not require an NVIDIA credential or network access.
- Isolate NeMo calls behind an adapter. Missing packages, credentials, and provider failures need explicit actionable errors.
- Never silently relabel offline output as NeMo-generated output.
- Sanitize artifact names and keep writes inside the configured artifact directory.
- Mock external provider calls in unit tests.

## Frontend guidance

- Treat API responses as untrusted and handle loading, empty, unavailable, and error states.
- Clearly label registry-only domains and disabled provider choices.
- Never expose server credentials. Any `NEXT_PUBLIC_*` value is visible to browsers.
- Run both ESLint and the production Next.js build before submitting.
- Keep accessibility basics intact: semantic controls, labels, focus states, keyboard operation, and meaningful status text.

## Adding a domain

A registry card and a working generator are separate deliverables. A domain should only be marked implemented when all relevant items are present:

- validated request and response schemas;
- generator implementation;
- deterministic tests for the offline path;
- API wiring and explicit capability metadata;
- frontend state that reflects actual backend availability;
- artifact handling and error coverage;
- user-facing documentation.

Until then, label the domain as planned or registry-only.

## Pull request checklist

- [ ] The change is scoped and explained.
- [ ] Backend tests pass.
- [ ] Frontend lint and build pass.
- [ ] New external calls are bounded and fail explicitly.
- [ ] No secrets, generated artifacts, or local environment files are committed.
- [ ] Documentation and capability labels match verified behavior.
- [ ] NeMo/native-renderer prerequisites are called out where relevant.

## Reporting security issues

Do not open a public issue for suspected vulnerabilities. Follow [SECURITY.md](SECURITY.md).
