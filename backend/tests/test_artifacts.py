from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageChops

from app.services.artifacts import ArtifactExporter, DegradationConfig, InvoiceRenderer
from app.services.generation import OfflineInvoiceGenerator
from app.services.persistence import SQLiteRepository


def test_renderer_writes_html_pdf_and_png(tmp_path: Path) -> None:
    invoice = OfflineInvoiceGenerator().generate(count=1, seed=21)[0]

    artifacts = InvoiceRenderer(tmp_path).render(invoice, index=1)

    assert {artifact.kind for artifact in artifacts} == {"html", "pdf", "png"}
    for artifact in artifacts:
        assert artifact.path.exists()
        assert artifact.path.stat().st_size > 20
    assert artifacts[0].path.read_text(encoding="utf-8").startswith("<!doctype html>")
    assert next(item.path for item in artifacts if item.kind == "pdf").read_bytes().startswith(b"%PDF")
    Image.open(next(item.path for item in artifacts if item.kind == "png")).verify()


def test_png_renderer_uses_fast_lossless_encoding(tmp_path: Path, monkeypatch) -> None:
    invoice = OfflineInvoiceGenerator().generate(count=1, seed=21)[0]
    options: dict[str, object] = {}
    original_save = Image.Image.save

    def capture_save(image, destination, *args, **kwargs):
        options.update(kwargs)
        return original_save(image, destination, *args, **kwargs)

    monkeypatch.setattr(Image.Image, "save", capture_save)

    InvoiceRenderer._write_png(invoice, tmp_path / "invoice.png")

    assert options["format"] == "PNG"
    assert options["optimize"] is False


def test_image_degradation_is_seeded_and_configurable(tmp_path: Path) -> None:
    invoice = OfflineInvoiceGenerator().generate(count=1, seed=22)[0]
    renderer = InvoiceRenderer(tmp_path)
    clean = next(item.path for item in renderer.render(invoice, index=1) if item.kind == "png")
    config = DegradationConfig(blur_radius=1.2, noise_sigma=12, jpeg_quality=55, rotation_degrees=1.5)

    first = renderer.degrade(clean, config=config, seed=8, suffix="first")
    second = renderer.degrade(clean, config=config, seed=8, suffix="second")

    with Image.open(first) as left, Image.open(second) as right, Image.open(clean) as original:
        assert ImageChops.difference(left.convert("RGB"), right.convert("RGB")).getbbox() is None
        assert ImageChops.difference(left.convert("RGB"), original.convert("RGB")).getbbox() is not None


def test_exporter_writes_json_jsonl_csv_parquet_and_huggingface_card(tmp_path: Path) -> None:
    invoices = OfflineInvoiceGenerator().generate(count=2, seed=23)

    artifacts = ArtifactExporter(tmp_path).export(invoices)

    kinds = {artifact.kind for artifact in artifacts}
    assert {"json", "jsonl", "csv", "parquet", "dataset-card"} <= kinds
    json_path = next(item.path for item in artifacts if item.kind == "json")
    assert len(json.loads(json_path.read_text(encoding="utf-8"))) == 2
    jsonl_path = next(item.path for item in artifacts if item.kind == "jsonl")
    assert len(jsonl_path.read_text(encoding="utf-8").splitlines()) == 2
    assert "invoice_number" in next(item.path for item in artifacts if item.kind == "csv").read_text(encoding="utf-8").splitlines()[0]
    assert "Hugging Face" in next(item.path for item in artifacts if item.kind == "dataset-card").read_text(encoding="utf-8")


def test_sqlite_repository_persists_jobs_artifacts_and_gallery(tmp_path: Path) -> None:
    repository = SQLiteRepository(tmp_path / "metadata.sqlite3")
    repository.create_job("job-1", {"domain": "invoices", "count": 2})
    repository.update_job("job-1", status="completed", progress=1.0, result={"quality_score": 1.0})
    repository.add_artifact("job-1", kind="json", path="job-1/invoices.json", size=42)

    job = repository.get_job("job-1")
    gallery = repository.list_gallery(limit=10)

    assert job is not None
    assert job["request"]["count"] == 2
    assert job["artifacts"][0]["url"] == "/artifacts/job-1/invoices.json"
    assert gallery[0]["id"] == "job-1"
    assert gallery[0]["quality_score"] == 1.0
