#!/usr/bin/env python
"""Exercise the credential-free NV-SynthForge API from generation through artifacts."""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any

BASE = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/") + "/api/v1"


def request(method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as response:
        if not 200 <= response.status < 300:
            raise AssertionError((path, response.status))
        return json.loads(response.read())


def download_artifact(path: str) -> int:
    origin = BASE.removesuffix("/api/v1")
    url = path if path.startswith(("http://", "https://")) else origin + path
    with urllib.request.urlopen(url, timeout=20) as response:
        payload = response.read()
        assert response.status == 200 and payload, (url, response.status)
        return len(payload)


def wait_for_job(job_id: str, timeout: float = 45) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = request("GET", f"/jobs/{job_id}")
        if state["status"] == "completed":
            return state
        if state["status"] == "failed":
            raise AssertionError(state)
        time.sleep(0.25)
    raise AssertionError(f"job {job_id} timed out")


def main() -> int:
    health = request("GET", "/health")
    assert health.get("status") == "ok" and health.get("offline_provider") is True, health

    domains_payload = request("GET", "/domains")
    domains = domains_payload.get("items", domains_payload.get("domains", []))
    assert any(item.get("id") == "invoices" or item.get("slug") == "invoice" for item in domains), domains
    assert any(item.get("id") == "healthcare" and item.get("available") is True for item in domains), domains

    created = request("POST", "/generate", {
        "domain": "invoices",
        "count": 2,
        "seed": 42,
        "provider": "offline",
        "language": "en-IN",
        "render": True,
        "degrade": True,
        "degradation": {"noise": 0.1, "blur": 0.1, "perspective": 0.05, "stamps": 0.1},
    })
    job_id = str(created.get("job_id") or created.get("id") or "")
    assert job_id, created

    state = wait_for_job(job_id)

    results = state["results"]
    assert len(results) == 2 and all(item["validation_score"] == 100 for item in results), state
    artifacts = {artifact["kind"]: artifact for artifact in state["artifacts"]}
    for required in ("html", "pdf", "png", "degraded-image", "json", "jsonl", "csv", "dataset-card"):
        assert required in artifacts, (required, sorted(artifacts))
    downloaded_bytes = download_artifact(artifacts["degraded-image"]["url"])

    gallery = request("GET", "/gallery")["items"]
    assert len([item for item in gallery if item.get("job_id") == job_id]) == 2, gallery

    benchmark = request("POST", "/benchmarks", {"job_id": job_id, "model": "ground-truth-self-check"})
    assert benchmark["accuracy"] == 1.0 and benchmark["documents"] == 2, benchmark

    healthcare_created = request("POST", "/generate", {
        "domain": "healthcare",
        "count": 2,
        "seed": 73,
        "provider": "offline",
        "language": "gu-IN",
        "render": False,
        "degrade": False,
    })
    healthcare_job_id = str(healthcare_created.get("job_id") or healthcare_created.get("id") or "")
    assert healthcare_job_id, healthcare_created
    healthcare_state = wait_for_job(healthcare_job_id)
    healthcare_results = healthcare_state["results"]
    assert len(healthcare_results) == 2, healthcare_state
    assert all(item["domain"] == "healthcare" and item["validation_score"] == 100 for item in healthcare_results)
    assert all(item["medical_note"]["synthetic"] is True for item in healthcare_results)
    healthcare_artifacts = {artifact["kind"]: artifact for artifact in healthcare_state["artifacts"]}
    assert {"json", "jsonl"}.issubset(healthcare_artifacts), healthcare_artifacts
    download_artifact(healthcare_artifacts["json"]["url"])

    print(json.dumps({
        "status": "passed",
        "invoice_job_id": job_id,
        "invoice_documents": len(results),
        "invoice_quality_score": state["quality_score"],
        "invoice_artifact_kinds": sorted(artifacts),
        "downloaded_degraded_image_bytes": downloaded_bytes,
        "healthcare_job_id": healthcare_job_id,
        "healthcare_documents": len(healthcare_results),
        "healthcare_quality_score": healthcare_state["quality_score"],
        "healthcare_artifact_kinds": sorted(healthcare_artifacts),
        "benchmark": {"accuracy": benchmark["accuracy"], "latency_ms": benchmark["latency_ms"], "throughput": benchmark["throughput"]},
    }, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, KeyError, urllib.error.URLError) as exc:
        print(f"E2E smoke failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
