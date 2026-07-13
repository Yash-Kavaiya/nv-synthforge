from __future__ import annotations

import os
import time
import uuid
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from app.domain.registry import list_domains
from app.providers.nemo import NemoInvoiceProvider
from app.services.artifacts import ArtifactExporter, DegradationConfig, InvoiceRenderer, StructuredArtifactExporter
from app.services.benchmarking import benchmark_for
from app.services.generation import OfflineInvoiceGenerator
from app.services.healthcare_generation import OfflineHealthcareGenerator
from app.services.legal_generation import OfflineLegalGenerator
from app.services.support_generation import OfflineSupportGenerator
from app.services.persistence import SQLiteRepository
from app.services.quality import (
    QualityReport,
    validate_invoice,
    validate_legal_contract,
    validate_medical_note,
    validate_support_conversation,
)


class DegradationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    noise: float = Field(default=0.18, ge=0, le=1)
    blur: float = Field(default=0.08, ge=0, le=1)
    perspective: float = Field(default=0.12, ge=0, le=1)
    stamps: float = Field(default=0.24, ge=0, le=1)

    def artifact_config(self) -> DegradationConfig:
        return DegradationConfig(
            blur_radius=round(self.blur * 5, 3),
            noise_sigma=round(self.noise * 30, 3),
            jpeg_quality=max(45, round(95 - self.noise * 45)),
            rotation_degrees=round(self.perspective * 2.5, 3),
            perspective=round(self.perspective * 0.08, 4),
            stamp_opacity=round(self.stamps, 3),
            contrast=round(1 - self.stamps * 0.2, 3),
        )


class HealthcareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    clinical_profile: Literal["mixed", "respiratory", "cardiovascular", "general"] = "mixed"
    include_medications: bool = True


class SupportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    industry: Literal["mixed", "telecom", "ecommerce", "banking", "saas"] = "mixed"
    sentiment_arc: Literal["recovery", "steady-positive", "escalation"] = "recovery"
    max_turns: int = Field(default=6, ge=4, le=10)


class LegalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_type: Literal["mixed", "nda", "service-agreement", "msa"] = "mixed"
    max_clauses: int = Field(default=6, ge=3, le=8)


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain: Literal["invoices", "invoice", "healthcare", "support", "legal"] = "invoices"
    count: int = Field(default=1, ge=1, le=100)
    seed: int = Field(default=42, ge=0, le=2_147_483_647)
    provider: Literal["offline", "nemo"] = "offline"
    language: Literal["en-IN", "hi-IN", "gu-IN"] = "en-IN"
    render: bool = True
    degrade: bool = False
    degradation: DegradationRequest = Field(default_factory=DegradationRequest)
    healthcare: HealthcareRequest = Field(default_factory=HealthcareRequest)
    support: SupportRequest = Field(default_factory=SupportRequest)
    legal: LegalRequest = Field(default_factory=LegalRequest)


class BenchmarkRequest(BaseModel):
    job_id: str | None = None
    name: str | None = None


def _package_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def _quality_rules(report: QualityReport) -> list[dict[str, Any]]:
    messages = {violation.rule: violation.message for violation in report.violations}
    definitions = [
        ("seller_gstin", "Seller GSTIN matches its state", "gstin_state_code"),
        ("buyer_gstin", "Buyer GSTIN matches its state", "gstin_state_code"),
        ("subtotal", "Line-item subtotals reconcile", "subtotal"),
        ("tax_total", "GST components reconcile", "tax_total"),
        ("grand_total", "Grand total reconciles", "grand_total"),
    ]
    return [
        {
            "id": rule_id,
            "label": label,
            "passed": violation_key not in messages,
            "detail": messages.get(violation_key, "Passed deterministic validation"),
        }
        for rule_id, label, violation_key in definitions
    ]


def _healthcare_quality_rules(report: QualityReport) -> list[dict[str, Any]]:
    messages = {violation.rule: violation.message for violation in report.violations}
    definitions = [
        ("synthetic_disclaimer", "Explicitly marked as synthetic"),
        ("pseudonymous_identity", "Patient identity is pseudonymous"),
        ("soap_completeness", "All SOAP sections are complete"),
        ("diagnosis", "ICD-10 diagnosis is present"),
        ("vitals", "Vital signs are internally consistent"),
    ]
    return [
        {
            "id": rule_id,
            "label": label,
            "passed": rule_id not in messages,
            "detail": messages.get(rule_id, "Passed deterministic validation"),
        }
        for rule_id, label in definitions
    ]


def _support_quality_rules(report: QualityReport) -> list[dict[str, Any]]:
    messages = {violation.rule: violation.message for violation in report.violations}
    definitions = [
        ("synthetic_disclaimer", "Explicitly marked as synthetic"),
        ("pseudonymous_identity", "Customer identity is pseudonymous"),
        ("turn_structure", "Customer and agent turns alternate"),
        ("resolution", "Resolution state matches the closing turn"),
        ("sentiment_arc", "Sentiment follows the configured arc"),
    ]
    return [
        {
            "id": rule_id,
            "label": label,
            "passed": rule_id not in messages,
            "detail": messages.get(rule_id, "Passed deterministic validation"),
        }
        for rule_id, label in definitions
    ]


def _legal_quality_rules(report: QualityReport) -> list[dict[str, Any]]:
    messages = {violation.rule: violation.message for violation in report.violations}
    definitions = [
        ("synthetic_disclaimer", "Explicitly marked as synthetic"),
        ("pseudonymous_identity", "Parties use synthetic identifiers"),
        ("party_distinctness", "Contract parties are distinct"),
        ("clause_structure", "Clauses are sequential and complete"),
        ("confidentiality", "Confidentiality coverage is present"),
    ]
    return [
        {
            "id": rule_id,
            "label": label,
            "passed": rule_id not in messages,
            "detail": messages.get(rule_id, "Passed deterministic validation"),
        }
        for rule_id, label in definitions
    ]


def _public_job(job: dict[str, Any]) -> dict[str, Any]:
    value = dict(job)
    value["progress"] = round(float(value.get("progress", 0)) * 100, 1)
    value.setdefault("results", [])
    return value


def create_app(data_dir: Path | None = None) -> FastAPI:
    root = Path(data_dir or os.getenv("SYNTHFORGE_DATA_DIR", ".data")).resolve()
    artifacts_root = root / "artifacts"
    artifacts_root.mkdir(parents=True, exist_ok=True)
    repository = SQLiteRepository(root / "metadata.sqlite3")

    application = FastAPI(
        title="NV-SynthForge API",
        version="0.1.0",
        description="Validated multimodal synthetic datasets powered by NVIDIA NeMo Data Designer.",
    )
    cors_origins = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
        ).split(",")
        if origin.strip()
    ]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.mount("/artifacts", StaticFiles(directory=artifacts_root), name="artifacts")
    application.state.repository = repository
    application.state.artifacts_root = artifacts_root

    def run_generation(job_id: str, request: GenerateRequest) -> None:
        started = time.perf_counter()
        try:
            repository.update_job(job_id, status="running", progress=0.05)
            if request.domain == "legal":
                if request.provider != "offline":
                    raise ValueError("NeMo generation is not yet configured for the legal domain; use provider='offline'")
                contracts = OfflineLegalGenerator().generate(
                    request.count,
                    request.seed,
                    request.language,
                    document_type=request.legal.document_type,
                    max_clauses=request.legal.max_clauses,
                )
                repository.update_job(job_id, progress=0.35)
                job_dir = artifacts_root / job_id
                records = [contract.model_dump(mode="json") for contract in contracts]
                documents: list[dict[str, Any]] = []
                quality_scores: list[float] = []
                for index, contract in enumerate(contracts, start=1):
                    report = validate_legal_contract(contract)
                    score = round(report.score * 100, 1)
                    quality_scores.append(score)
                    documents.append(
                        {
                            "id": f"{job_id}-legal-contract-{index}",
                            "title": f"{contract.title} · {contract.contract_id}",
                            "domain": "legal",
                            "language": request.language,
                            "provider": request.provider,
                            "contract_id": contract.contract_id,
                            "document_type": contract.document_type,
                            "validation_score": score,
                            "status": "validated" if report.valid else "review",
                            "rules": _legal_quality_rules(report),
                            "file_urls": {},
                            "contract": contract.model_dump(mode="json"),
                        }
                    )
                    repository.update_job(
                        job_id,
                        progress=0.35 + 0.45 * index / max(len(contracts), 1),
                    )

                exports = StructuredArtifactExporter(job_dir).export(records, "legal-contracts")
                json_url = ""
                for artifact in exports:
                    relative = artifact.path.relative_to(artifacts_root).as_posix()
                    repository.add_artifact(
                        job_id,
                        kind=artifact.kind,
                        path=relative,
                        size=artifact.path.stat().st_size,
                    )
                    if artifact.kind == "json":
                        json_url = f"/artifacts/{relative}"
                for document in documents:
                    document["file_urls"]["json"] = json_url

                elapsed = max(time.perf_counter() - started, 0.001)
                repository.update_job(
                    job_id,
                    status="completed",
                    progress=1.0,
                    result={
                        "results": documents,
                        "quality_score": round(sum(quality_scores) / len(quality_scores), 1),
                        "document_count": len(documents),
                        "duration_ms": round(elapsed * 1000, 2),
                        "throughput": round(len(documents) / elapsed, 2),
                    },
                )
                return

            if request.domain == "support":
                if request.provider != "offline":
                    raise ValueError("NeMo generation is not yet configured for the support domain; use provider='offline'")
                conversations = OfflineSupportGenerator().generate(
                    request.count,
                    request.seed,
                    request.language,
                    industry=request.support.industry,
                    sentiment_arc=request.support.sentiment_arc,
                    max_turns=request.support.max_turns,
                )
                repository.update_job(job_id, progress=0.35)
                job_dir = artifacts_root / job_id
                records = [conversation.model_dump(mode="json") for conversation in conversations]
                documents: list[dict[str, Any]] = []
                quality_scores: list[float] = []
                for index, conversation in enumerate(conversations, start=1):
                    report = validate_support_conversation(conversation)
                    score = round(report.score * 100, 1)
                    quality_scores.append(score)
                    documents.append(
                        {
                            "id": f"{job_id}-support-conversation-{index}",
                            "title": f"Support conversation · {conversation.conversation_id}",
                            "domain": "support",
                            "language": request.language,
                            "provider": request.provider,
                            "conversation_id": conversation.conversation_id,
                            "customer_id": conversation.customer_id,
                            "issue_type": conversation.issue_type,
                            "validation_score": score,
                            "status": "validated" if report.valid else "review",
                            "rules": _support_quality_rules(report),
                            "file_urls": {},
                            "conversation": conversation.model_dump(mode="json"),
                        }
                    )
                    repository.update_job(
                        job_id,
                        progress=0.35 + 0.45 * index / max(len(conversations), 1),
                    )

                exports = StructuredArtifactExporter(job_dir).export(records, "support-conversations")
                json_url = ""
                for artifact in exports:
                    relative = artifact.path.relative_to(artifacts_root).as_posix()
                    repository.add_artifact(
                        job_id,
                        kind=artifact.kind,
                        path=relative,
                        size=artifact.path.stat().st_size,
                    )
                    if artifact.kind == "json":
                        json_url = f"/artifacts/{relative}"
                for document in documents:
                    document["file_urls"]["json"] = json_url

                elapsed = max(time.perf_counter() - started, 0.001)
                repository.update_job(
                    job_id,
                    status="completed",
                    progress=1.0,
                    result={
                        "results": documents,
                        "quality_score": round(sum(quality_scores) / len(quality_scores), 1),
                        "document_count": len(documents),
                        "duration_ms": round(elapsed * 1000, 2),
                        "throughput": round(len(documents) / elapsed, 2),
                    },
                )
                return

            if request.domain == "healthcare":
                if request.provider != "offline":
                    raise ValueError("NeMo generation is not yet configured for the healthcare domain; use provider='offline'")
                notes = OfflineHealthcareGenerator().generate(
                    request.count,
                    request.seed,
                    request.language,
                    clinical_profile=request.healthcare.clinical_profile,
                    include_medications=request.healthcare.include_medications,
                )
                repository.update_job(job_id, progress=0.35)
                job_dir = artifacts_root / job_id
                records = [note.model_dump(mode="json") for note in notes]
                documents: list[dict[str, Any]] = []
                quality_scores: list[float] = []
                for index, note in enumerate(notes, start=1):
                    report = validate_medical_note(note)
                    score = round(report.score * 100, 1)
                    quality_scores.append(score)
                    documents.append(
                        {
                            "id": f"{job_id}-medical-note-{index}",
                            "title": f"Medical note · {note.note_id}",
                            "domain": "healthcare",
                            "language": request.language,
                            "provider": request.provider,
                            "note_id": note.note_id,
                            "patient": note.patient.name,
                            "validation_score": score,
                            "status": "validated" if report.valid else "review",
                            "rules": _healthcare_quality_rules(report),
                            "file_urls": {},
                            "medical_note": note.model_dump(mode="json"),
                        }
                    )
                    repository.update_job(job_id, progress=0.35 + 0.45 * index / max(len(notes), 1))

                exports = StructuredArtifactExporter(job_dir).export(records, "medical-notes")
                json_url = ""
                for artifact in exports:
                    relative = artifact.path.relative_to(artifacts_root).as_posix()
                    repository.add_artifact(
                        job_id,
                        kind=artifact.kind,
                        path=relative,
                        size=artifact.path.stat().st_size,
                    )
                    if artifact.kind == "json":
                        json_url = f"/artifacts/{relative}"
                for document in documents:
                    document["file_urls"]["json"] = json_url

                elapsed = max(time.perf_counter() - started, 0.001)
                repository.update_job(
                    job_id,
                    status="completed",
                    progress=1.0,
                    result={
                        "results": documents,
                        "quality_score": round(sum(quality_scores) / len(quality_scores), 1),
                        "document_count": len(documents),
                        "duration_ms": round(elapsed * 1000, 2),
                        "throughput": round(len(documents) / elapsed, 2),
                    },
                )
                return

            if request.provider == "nemo":
                invoices = NemoInvoiceProvider().generate(request.count, request.seed)
            else:
                invoices = OfflineInvoiceGenerator().generate(request.count, request.seed)
            repository.update_job(job_id, progress=0.35)

            job_dir = artifacts_root / job_id
            job_dir.mkdir(parents=True, exist_ok=True)
            renderer = InvoiceRenderer(job_dir)
            documents: list[dict[str, Any]] = []
            quality_scores: list[float] = []

            for index, invoice in enumerate(invoices, start=1):
                report = validate_invoice(invoice)
                score = round(report.score * 100, 1)
                quality_scores.append(score)
                file_urls: dict[str, str] = {}
                document_artifacts = []
                if request.render:
                    document_artifacts = renderer.render(invoice, index=index, language=request.language)
                    png = next((artifact.path for artifact in document_artifacts if artifact.kind == "png"), None)
                    if request.degrade and png is not None:
                        degraded = renderer.degrade(
                            png,
                            config=request.degradation.artifact_config(),
                            seed=request.seed + index,
                        )
                        document_artifacts.append(type(document_artifacts[0])("degraded-image", degraded))

                for artifact in document_artifacts:
                    relative = artifact.path.relative_to(artifacts_root).as_posix()
                    repository.add_artifact(
                        job_id,
                        kind=artifact.kind,
                        path=relative,
                        size=artifact.path.stat().st_size,
                    )
                    if artifact.kind == "pdf":
                        file_urls["pdf"] = f"/artifacts/{relative}"
                    elif artifact.kind == "png":
                        file_urls["image"] = f"/artifacts/{relative}"
                    elif artifact.kind == "degraded-image":
                        file_urls["degraded_image"] = f"/artifacts/{relative}"

                documents.append(
                    {
                        "id": f"{job_id}-invoice-{index}",
                        "title": f"Invoice · {invoice.seller.name}",
                        "domain": "invoices",
                        "language": request.language,
                        "provider": request.provider,
                        "invoice_number": invoice.invoice_number,
                        "vendor": invoice.seller.name,
                        "amount": f"₹{invoice.grand_total:,.2f}",
                        "validation_score": score,
                        "status": "validated" if report.valid else "review",
                        "rules": _quality_rules(report),
                        "file_urls": file_urls,
                        "invoice": invoice.model_dump(mode="json"),
                    }
                )
                repository.update_job(
                    job_id,
                    progress=0.35 + 0.45 * index / max(len(invoices), 1),
                )

            exports = ArtifactExporter(job_dir).export(invoices)
            json_url = ""
            for artifact in exports:
                relative = artifact.path.relative_to(artifacts_root).as_posix()
                repository.add_artifact(
                    job_id,
                    kind=artifact.kind,
                    path=relative,
                    size=artifact.path.stat().st_size,
                )
                if artifact.kind == "json":
                    json_url = f"/artifacts/{relative}"
            for document in documents:
                if json_url:
                    document["file_urls"]["json"] = json_url

            elapsed = max(time.perf_counter() - started, 0.001)
            repository.update_job(
                job_id,
                status="completed",
                progress=1.0,
                result={
                    "results": documents,
                    "quality_score": round(sum(quality_scores) / len(quality_scores), 1),
                    "document_count": len(documents),
                    "duration_ms": round(elapsed * 1000, 2),
                    "throughput": round(len(documents) / elapsed, 2),
                },
            )
        except Exception as exc:  # job errors must remain observable through status endpoints
            repository.update_job(job_id, status="failed", progress=1.0, error=str(exc))

    @application.get("/api/v1/health", tags=["system"])
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "NV-SynthForge API",
            "version": "0.1.0",
            "offline_provider": True,
            "nemo_version": _package_version("data-designer"),
            "nemo_configured": bool(os.getenv("NVIDIA_API_KEY")),
        }

    @application.get("/api/v1/domains", tags=["domains"])
    def domains() -> dict[str, Any]:
        registered = list_domains()
        planned = [
            ("finance", "Finance", "Statements and reconciled financial reports"),
            ("hr", "HR & Recruiting", "Resumes, offers, and performance reviews"),
            ("retail", "Retail", "Products, reviews, and commerce support data"),
        ]
        items = [
            {
                "id": "invoices" if domain.slug == "invoice" else domain.slug,
                "slug": domain.slug,
                "name": domain.name,
                "description": domain.description,
                "available": True,
                "supports": sorted(domain.supports),
            }
            for domain in registered
        ]
        items.extend(
            {"id": slug, "slug": slug, "name": name, "description": description, "available": False, "supports": ["json"]}
            for slug, name, description in planned
        )
        return {"domains": items}

    @application.post("/api/v1/generate", status_code=status.HTTP_202_ACCEPTED, tags=["generation"])
    def generate(request: GenerateRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
        job_id = uuid.uuid4().hex
        repository.create_job(job_id, request.model_dump(mode="json"))
        background_tasks.add_task(run_generation, job_id, request)
        return _public_job(repository.get_job(job_id) or {"job_id": job_id, "status": "queued"})

    @application.get("/api/v1/jobs/{job_id}", tags=["generation"])
    def get_job(job_id: str) -> dict[str, Any]:
        job = repository.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return _public_job(job)

    @application.websocket("/api/v1/jobs/{job_id}/ws")
    async def job_progress(websocket: WebSocket, job_id: str) -> None:
        await websocket.accept()
        try:
            while True:
                job = repository.get_job(job_id)
                if job is None:
                    await websocket.send_json({"status": "failed", "error": "Job not found"})
                    break
                public = _public_job(job)
                await websocket.send_json(public)
                if job["status"] in {"completed", "failed"}:
                    break
                import asyncio

                await asyncio.sleep(0.15)
        except WebSocketDisconnect:
            return
        finally:
            await websocket.close()

    @application.get("/api/v1/gallery", tags=["gallery"])
    def gallery(limit: Annotated[int, Query(ge=1, le=100)] = 50) -> dict[str, Any]:
        items: list[dict[str, Any]] = []
        for job in repository.list_gallery(limit=limit):
            for document in job.get("results", []):
                items.append(
                    {
                        **document,
                        "job_id": job["id"],
                        "created_at": job.get("created_at"),
                    }
                )
        return {"items": items[:limit]}

    @application.get("/api/v1/benchmarks", tags=["benchmarks"])
    def benchmarks(limit: Annotated[int, Query(ge=1, le=100)] = 20) -> dict[str, Any]:
        return {"benchmarks": [benchmark_for(job) for job in repository.list_gallery(limit=limit)]}

    @application.post("/api/v1/benchmarks", tags=["benchmarks"])
    def run_benchmark(request: BenchmarkRequest) -> dict[str, Any]:
        if request.job_id:
            job = repository.get_job(request.job_id)
        else:
            gallery_items = repository.list_gallery(limit=1)
            job = gallery_items[0] if gallery_items else None
        if job is None or job.get("status") != "completed":
            raise HTTPException(status_code=404, detail="Completed generation job not found")
        return benchmark_for(job, request.name)

    return application


app = create_app()
