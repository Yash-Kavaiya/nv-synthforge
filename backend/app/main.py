from __future__ import annotations

import asyncio
import os
import uuid
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Annotated, Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.domain.registry import list_domains
from app.schemas import (
    NEMO_DOMAINS,
    BenchmarkRequest,
    DegradationRequest,
    FinanceRequest,
    GenerateRequest,
    HealthcareRequest,
    HRRequest,
    LegalRequest,
    OCREvalRequest,
    RetailRequest,
    SupportRequest,
)
from app.services.benchmarking import benchmark_for
from app.services.jobs import GenerationRunner
from app.services.ocr_eval import evaluate_ocr_prediction, make_noisy_prediction
from app.services.persistence import SQLiteRepository

API_VERSION = "0.1.0"
_TERMINAL_STATUSES = frozenset({"completed", "failed"})
_WS_POLL_SECONDS = 0.15

# Re-exported for callers that imported request models from app.main before app.schemas existed.
__all__ = [
    "BenchmarkRequest",
    "DegradationRequest",
    "FinanceRequest",
    "GenerateRequest",
    "HRRequest",
    "HealthcareRequest",
    "LegalRequest",
    "OCREvalRequest",
    "RetailRequest",
    "SupportRequest",
    "app",
    "create_app",
]


def _package_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def _public_job(job: dict[str, Any]) -> dict[str, Any]:
    value = dict(job)
    value["progress"] = round(float(value.get("progress", 0)) * 100, 1)
    value.setdefault("results", [])
    return value


def _is_invoice_job(job: dict[str, Any]) -> bool:
    return str(job.get("request", {}).get("domain", "invoices")) in {"invoices", "invoice"}


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def create_app(data_dir: Path | None = None) -> FastAPI:
    root = Path(data_dir if data_dir is not None else os.getenv("SYNTHFORGE_DATA_DIR", ".data")).resolve()
    artifacts_root = root / "artifacts"
    artifacts_root.mkdir(parents=True, exist_ok=True)
    repository = SQLiteRepository(root / "metadata.sqlite3")
    # Background tasks do not survive a restart; anything still in flight can never finish.
    repository.fail_interrupted_jobs()
    runner = GenerationRunner(repository, artifacts_root)

    application = FastAPI(
        title="NV-SynthForge API",
        version=API_VERSION,
        description="Validated multimodal synthetic datasets powered by NVIDIA NeMo Data Designer.",
    )
    origins = _cors_origins()
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        # Browsers reject credentialed requests to a wildcard origin, so only allow credentials for explicit lists.
        allow_credentials="*" not in origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.mount("/artifacts", StaticFiles(directory=artifacts_root), name="artifacts")
    application.state.repository = repository
    application.state.artifacts_root = artifacts_root

    @application.get("/api/v1/health", tags=["system"])
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "NV-SynthForge API",
            "version": API_VERSION,
            "offline_provider": True,
            "nemo_version": _package_version("data-designer"),
            "nemo_configured": bool(os.getenv("NVIDIA_API_KEY")),
        }

    @application.get("/api/v1/domains", tags=["domains"])
    def domains() -> dict[str, Any]:
        stats = repository.domain_stats()
        items = []
        for domain in list_domains():
            domain_id = "invoices" if domain.slug == "invoice" else domain.slug
            domain_stats = stats.get(domain_id, {})
            items.append(
                {
                    "id": domain_id,
                    "slug": domain.slug,
                    "name": domain.name,
                    "description": domain.description,
                    "available": True,
                    "supports": sorted(domain.supports),
                    "providers": ["offline", "nemo"] if domain_id in NEMO_DOMAINS else ["offline"],
                    "generated": int(domain_stats.get("generated", 0)),
                    "accuracy": domain_stats.get("accuracy"),
                }
            )
        return {"domains": items}

    @application.post("/api/v1/generate", status_code=status.HTTP_202_ACCEPTED, tags=["generation"])
    def generate(request: GenerateRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
        job_id = uuid.uuid4().hex
        job = repository.create_job(job_id, request.model_dump(mode="json"))
        background_tasks.add_task(runner.run, job_id, request)
        return _public_job(job or {"job_id": job_id, "status": "queued"})

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
                job = await asyncio.to_thread(repository.get_job, job_id)
                if job is None:
                    await websocket.send_json({"status": "failed", "error": "Job not found"})
                    break
                await websocket.send_json(_public_job(job))
                if job["status"] in _TERMINAL_STATUSES:
                    break
                await asyncio.sleep(_WS_POLL_SECONDS)
        except WebSocketDisconnect:
            return  # the client is gone; closing again would raise
        await websocket.close()

    @application.get("/api/v1/gallery", tags=["gallery"])
    def gallery(limit: Annotated[int, Query(ge=1, le=100)] = 50) -> dict[str, Any]:
        items: list[dict[str, Any]] = []
        for job in repository.list_gallery(limit=limit):
            for document in job.get("results", []):
                items.append({**document, "job_id": job["id"], "created_at": job.get("created_at")})
                if len(items) >= limit:
                    return {"items": items}
        return {"items": items}

    @application.get("/api/v1/benchmarks", tags=["benchmarks"])
    def benchmarks(limit: Annotated[int, Query(ge=1, le=100)] = 20) -> dict[str, Any]:
        return {"benchmarks": [benchmark_for(job) for job in repository.list_gallery(limit=limit)]}

    @application.post("/api/v1/benchmarks", tags=["benchmarks"])
    def run_benchmark(request: BenchmarkRequest) -> dict[str, Any]:
        if request.job_id:
            job = repository.get_job(request.job_id)
        else:
            latest = repository.list_gallery(limit=1)
            job = latest[0] if latest else None
        if job is None or job.get("status") != "completed":
            raise HTTPException(status_code=404, detail="Completed generation job not found")
        return benchmark_for(job, request.name)

    def _resolve_invoice_ground_truth(
        job_id: str | None, document_index: int, inline: dict[str, Any] | None
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        if inline is not None:
            return inline, None
        if not job_id:
            raise HTTPException(status_code=400, detail="Provide job_id or ground_truth invoice JSON")
        job = repository.get_job(job_id)
        if job is None or job.get("status") != "completed":
            raise HTTPException(status_code=404, detail="Completed generation job not found")
        if not _is_invoice_job(job):
            raise HTTPException(status_code=400, detail="OCR structure eval currently supports invoice jobs only")
        results = job.get("results") or []
        if document_index >= len(results):
            raise HTTPException(status_code=404, detail="Document index out of range for job")
        document = results[document_index]
        invoice = document.get("invoice")
        if not isinstance(invoice, dict):
            raise HTTPException(status_code=400, detail="Job document does not contain invoice ground truth")
        return invoice, {
            "job_id": job["id"],
            "document_id": document.get("id"),
            "title": document.get("title"),
            "file_urls": document.get("file_urls", {}),
            "artifacts": job.get("artifacts", []),
        }

    @application.post("/api/v1/ocr/evaluate", tags=["ocr"])
    def evaluate_ocr(request: OCREvalRequest) -> dict[str, Any]:
        ground_truth, context = _resolve_invoice_ground_truth(request.job_id, request.document_index, request.ground_truth)
        if request.demo_noise is not None:
            prediction = make_noisy_prediction(ground_truth, noise_level=request.demo_noise)
        elif request.prediction is not None:
            prediction = request.prediction
        else:
            raise HTTPException(status_code=400, detail="Provide prediction JSON or demo_noise for synthetic OCR output")
        report = evaluate_ocr_prediction(ground_truth=ground_truth, prediction=prediction, model_name=request.model_name)
        return {**report, "ground_truth": ground_truth, "prediction": prediction, "context": context}

    @application.get("/api/v1/ocr/samples", tags=["ocr"])
    def ocr_samples(limit: Annotated[int, Query(ge=1, le=50)] = 12) -> dict[str, Any]:
        samples: list[dict[str, Any]] = []
        for job in repository.list_gallery(limit=100):
            if not _is_invoice_job(job):
                continue
            for index, document in enumerate(job.get("results") or []):
                invoice = document.get("invoice")
                if not isinstance(invoice, dict):
                    continue
                samples.append(
                    {
                        "job_id": job["id"],
                        "document_index": index,
                        "document_id": document.get("id"),
                        "title": document.get("title"),
                        "language": document.get("language"),
                        "validation_score": document.get("validation_score"),
                        "file_urls": document.get("file_urls", {}),
                        "invoice_number": invoice.get("invoice_number"),
                        "grand_total": invoice.get("grand_total"),
                    }
                )
                if len(samples) >= limit:
                    return {"samples": samples}
        return {"samples": samples}

    return application


app = create_app()
