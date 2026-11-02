"""Background generation jobs: generate, validate, export, and persist one batch."""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.providers.nemo import NemoInvoiceProvider
from app.schemas import GenerateRequest
from app.services.artifacts import Artifact, ArtifactExporter, InvoiceRenderer, StructuredArtifactExporter
from app.services.finance_generation import OfflineFinanceGenerator
from app.services.generation import OfflineInvoiceGenerator
from app.services.healthcare_generation import OfflineHealthcareGenerator
from app.services.hr_generation import OfflineHRGenerator
from app.services.legal_generation import OfflineLegalGenerator
from app.services.persistence import SQLiteRepository
from app.services.quality import (
    QualityReport,
    rule_checks,
    validate_finance_statement,
    validate_hr_record,
    validate_invoice,
    validate_legal_contract,
    validate_medical_note,
    validate_retail_product,
    validate_support_conversation,
)
from app.services.retail_generation import OfflineRetailGenerator
from app.services.support_generation import OfflineSupportGenerator

# Progress milestones reported while a job runs (0..1).
_PROGRESS_GENERATED = 0.35
_PROGRESS_VALIDATION_SPAN = 0.45


@dataclass(frozen=True)
class StructuredDomain:
    """How one JSON-only domain is generated, validated, and summarized for the gallery."""

    document_slug: str  # used in document ids, e.g. "<job>-legal-contract-1"
    export_stem: str  # artifact file stem, e.g. "legal-contracts.json"
    payload_key: str  # key holding the full record in each gallery document
    generate: Callable[[GenerateRequest], Sequence[Any]]
    validate: Callable[[Any], QualityReport]
    summarize: Callable[[Any], dict[str, Any]]  # title plus domain-specific index fields


STRUCTURED_DOMAINS: dict[str, StructuredDomain] = {
    "healthcare": StructuredDomain(
        document_slug="medical-note",
        export_stem="medical-notes",
        payload_key="medical_note",
        generate=lambda r: OfflineHealthcareGenerator().generate(
            r.count, r.seed, r.language,
            clinical_profile=r.healthcare.clinical_profile,
            include_medications=r.healthcare.include_medications,
        ),
        validate=validate_medical_note,
        summarize=lambda n: {"title": f"Medical note · {n.note_id}", "note_id": n.note_id, "patient": n.patient.name},
    ),
    "support": StructuredDomain(
        document_slug="support-conversation",
        export_stem="support-conversations",
        payload_key="conversation",
        generate=lambda r: OfflineSupportGenerator().generate(
            r.count, r.seed, r.language,
            industry=r.support.industry,
            sentiment_arc=r.support.sentiment_arc,
            max_turns=r.support.max_turns,
        ),
        validate=validate_support_conversation,
        summarize=lambda c: {
            "title": f"Support conversation · {c.conversation_id}",
            "conversation_id": c.conversation_id,
            "customer_id": c.customer_id,
            "issue_type": c.issue_type,
        },
    ),
    "legal": StructuredDomain(
        document_slug="legal-contract",
        export_stem="legal-contracts",
        payload_key="contract",
        generate=lambda r: OfflineLegalGenerator().generate(
            r.count, r.seed, r.language,
            document_type=r.legal.document_type,
            max_clauses=r.legal.max_clauses,
        ),
        validate=validate_legal_contract,
        summarize=lambda c: {
            "title": f"{c.title} · {c.contract_id}",
            "contract_id": c.contract_id,
            "document_type": c.document_type,
        },
    ),
    "finance": StructuredDomain(
        document_slug="finance-statement",
        export_stem="finance-statements",
        payload_key="statement",
        generate=lambda r: OfflineFinanceGenerator().generate(
            r.count, r.seed, r.language,
            statement_type=r.finance.statement_type,
            max_lines=r.finance.max_lines,
        ),
        validate=validate_finance_statement,
        summarize=lambda s: {
            "title": f"{s.title} · {s.statement_id}",
            "statement_id": s.statement_id,
            "statement_type": s.statement_type,
        },
    ),
    "hr": StructuredDomain(
        document_slug="hr-record",
        export_stem="hr-records",
        payload_key="hr_record",
        generate=lambda r: OfflineHRGenerator().generate(
            r.count, r.seed, r.language,
            document_type=r.hr.document_type,
            max_sections=r.hr.max_sections,
        ),
        validate=validate_hr_record,
        summarize=lambda h: {
            "title": f"{h.title} · {h.record_id}",
            "record_id": h.record_id,
            "document_type": h.document_type,
        },
    ),
    "retail": StructuredDomain(
        document_slug="retail-product",
        export_stem="retail-products",
        payload_key="product",
        generate=lambda r: OfflineRetailGenerator().generate(
            r.count, r.seed, r.language,
            category=r.retail.category,
            max_reviews=r.retail.max_reviews,
        ),
        validate=validate_retail_product,
        summarize=lambda p: {
            "title": f"{p.title} · {p.product_id}",
            "product_id": p.product_id,
            "category": p.category,
        },
    ),
}

_INVOICE_URL_KEYS = {"pdf": "pdf", "png": "image", "degraded-image": "degraded_image"}


class GenerationRunner:
    """Runs a generation request to completion and records the outcome on the job row."""

    def __init__(self, repository: SQLiteRepository, artifacts_root: Path) -> None:
        self.repository = repository
        self.artifacts_root = artifacts_root

    def run(self, job_id: str, request: GenerateRequest) -> None:
        started = time.perf_counter()
        try:
            self.repository.update_job(job_id, status="running", progress=0.05)
            domain = request.canonical_domain
            if domain in STRUCTURED_DOMAINS:
                documents = self._run_structured(job_id, request, STRUCTURED_DOMAINS[domain])
            else:
                documents = self._run_invoices(job_id, request)
            self._complete(job_id, documents, started)
        except Exception as exc:  # job errors must remain observable through status endpoints
            self.repository.update_job(job_id, status="failed", progress=1.0, error=str(exc))

    def _run_structured(self, job_id: str, request: GenerateRequest, spec: StructuredDomain) -> list[dict[str, Any]]:
        records = list(spec.generate(request))
        self.repository.update_job(job_id, progress=_PROGRESS_GENERATED)
        domain = request.canonical_domain
        documents = []
        for index, item in enumerate(records, start=1):
            report = spec.validate(item)
            documents.append(
                self._document(
                    job_id, request, report,
                    document_id=f"{job_id}-{spec.document_slug}-{index}",
                    fields=spec.summarize(item),
                    payload={spec.payload_key: item.model_dump(mode="json")},
                    rules=rule_checks(report, domain),
                )
            )
            self._report_progress(job_id, index, len(records))

        exports = StructuredArtifactExporter(self.artifacts_root / job_id).export(
            [item.model_dump(mode="json") for item in records], spec.export_stem
        )
        self._attach_json_url(documents, self._persist_artifacts(job_id, exports))
        return documents

    def _run_invoices(self, job_id: str, request: GenerateRequest) -> list[dict[str, Any]]:
        if request.provider == "nemo":
            invoices = NemoInvoiceProvider().generate(request.count, request.seed)
        else:
            invoices = OfflineInvoiceGenerator().generate(request.count, request.seed)
        self.repository.update_job(job_id, progress=_PROGRESS_GENERATED)

        job_dir = self.artifacts_root / job_id
        renderer = InvoiceRenderer(job_dir)
        documents = []
        for index, invoice in enumerate(invoices, start=1):
            report = validate_invoice(invoice)
            rendered: list[Artifact] = []
            if request.render:
                rendered = renderer.render(invoice, index=index, language=request.language)
                png = next((artifact.path for artifact in rendered if artifact.kind == "png"), None)
                if request.degrade and png is not None:
                    degraded = renderer.degrade(png, config=request.degradation.artifact_config(), seed=request.seed + index)
                    rendered.append(Artifact("degraded-image", degraded))
            urls = self._persist_artifacts(job_id, rendered)
            documents.append(
                self._document(
                    job_id, request, report,
                    document_id=f"{job_id}-invoice-{index}",
                    fields={
                        "title": f"Invoice · {invoice.seller.name}",
                        "invoice_number": invoice.invoice_number,
                        "vendor": invoice.seller.name,
                        "amount": f"₹{invoice.grand_total:,.2f}",
                    },
                    payload={"invoice": invoice.model_dump(mode="json")},
                    rules=rule_checks(report, "invoices"),
                    file_urls={_INVOICE_URL_KEYS[kind]: url for kind, url in urls.items() if kind in _INVOICE_URL_KEYS},
                )
            )
            self._report_progress(job_id, index, len(invoices))

        exports = ArtifactExporter(job_dir).export(invoices)
        self._attach_json_url(documents, self._persist_artifacts(job_id, exports))
        return documents

    @staticmethod
    def _document(
        job_id: str,
        request: GenerateRequest,
        report: QualityReport,
        *,
        document_id: str,
        fields: dict[str, Any],
        payload: dict[str, Any],
        rules: list[dict[str, Any]],
        file_urls: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        return {
            "id": document_id,
            "domain": request.canonical_domain,
            "language": request.language,
            "provider": request.provider,
            **fields,
            "validation_score": round(report.score * 100, 1),
            "status": "validated" if report.valid else "review",
            "rules": rules,
            "file_urls": dict(file_urls or {}),
            **payload,
        }

    def _persist_artifacts(self, job_id: str, artifacts: Sequence[Artifact]) -> dict[str, str]:
        """Record artifacts on the job and return their public URLs keyed by kind."""
        urls: dict[str, str] = {}
        for artifact in artifacts:
            relative = artifact.path.relative_to(self.artifacts_root).as_posix()
            self.repository.add_artifact(job_id, kind=artifact.kind, path=relative, size=artifact.path.stat().st_size)
            urls[artifact.kind] = f"/artifacts/{relative}"
        return urls

    @staticmethod
    def _attach_json_url(documents: list[dict[str, Any]], urls: dict[str, str]) -> None:
        if "json" in urls:
            for document in documents:
                document["file_urls"]["json"] = urls["json"]

    def _report_progress(self, job_id: str, index: int, total: int) -> None:
        self.repository.update_job(
            job_id, progress=_PROGRESS_GENERATED + _PROGRESS_VALIDATION_SPAN * index / max(total, 1)
        )

    def _complete(self, job_id: str, documents: list[dict[str, Any]], started: float) -> None:
        elapsed = max(time.perf_counter() - started, 0.001)
        scores = [float(document["validation_score"]) for document in documents]
        self.repository.update_job(
            job_id,
            status="completed",
            progress=1.0,
            result={
                "results": documents,
                "quality_score": round(sum(scores) / len(scores), 1) if scores else 0.0,
                "document_count": len(documents),
                "duration_ms": round(elapsed * 1000, 2),
                "throughput": round(len(documents) / elapsed, 2),
            },
        )

