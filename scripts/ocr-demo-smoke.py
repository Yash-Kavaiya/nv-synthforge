#!/usr/bin/env python
"""Track C OCR harness smoke test.

Exercises the full demo loop against a running NV-SynthForge backend:

    generate invoices  ->  GET /ocr/samples  ->  POST /ocr/evaluate (demo_noise)

Exits non-zero on any failure so it is safe to wire into CI or a pre-demo check.

The API base is read from the ``API_BASE`` environment variable and defaults to
``http://127.0.0.1:8000``. If that base is unreachable the script also probes the
demo launcher's fallback ports (8001, 8002) before giving up.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any

DEFAULT_BASE = "http://127.0.0.1:8000"
FALLBACK_PORTS = (8000, 8001, 8002)


def _candidate_bases() -> list[str]:
    """Ordered, de-duplicated list of API bases to try (env first, then fallbacks)."""
    bases: list[str] = []
    env_base = os.getenv("API_BASE", DEFAULT_BASE).rstrip("/")
    if env_base:
        bases.append(env_base)
    for port in FALLBACK_PORTS:
        bases.append(f"http://127.0.0.1:{port}")
    seen: set[str] = set()
    ordered: list[str] = []
    for base in bases:
        if base not in seen:
            seen.add(base)
            ordered.append(base)
    return ordered


def _http(method: str, url: str, body: dict[str, Any] | None = None, timeout: float = 20) -> Any:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        if not 200 <= response.status < 300:
            raise AssertionError((url, response.status))
        return json.loads(response.read())


def _resolve_base() -> str:
    healthy_without_ocr: list[str] = []
    for base in _candidate_bases():
        try:
            health = _http("GET", f"{base}/api/v1/health", timeout=3)
        except (urllib.error.URLError, OSError, ValueError):
            continue
        if not (isinstance(health, dict) and health.get("status") == "ok"):
            continue
        # Confirm the OCR harness endpoints exist so we skip a stale build that is
        # healthy but predates /api/v1/ocr (a 404 here means wrong/old backend).
        try:
            _http("GET", f"{base}/api/v1/ocr/samples", timeout=3)
        except urllib.error.HTTPError:
            healthy_without_ocr.append(base)
            continue
        except (urllib.error.URLError, OSError, ValueError):
            continue
        return base
    if healthy_without_ocr:
        raise AssertionError(
            f"Backend(s) {', '.join(healthy_without_ocr)} are healthy but do not expose "
            "/api/v1/ocr — restart the backend with the current code."
        )
    raise AssertionError(
        f"No healthy backend on any of: {', '.join(_candidate_bases())}. "
        "Start it with scripts/demo-track-c.sh (or set API_BASE)."
    )


def _wait_for_job(api: str, job_id: str, timeout: float = 60) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = _http("GET", f"{api}/jobs/{job_id}")
        if state.get("status") == "completed":
            return state
        if state.get("status") == "failed":
            raise AssertionError(("generation failed", state))
        time.sleep(0.3)
    raise AssertionError(f"job {job_id} timed out after {timeout}s")


def main() -> int:
    base = _resolve_base()
    api = f"{base}/api/v1"
    print(f"Using backend: {base}")

    # 1) Generate a small invoice pack with rendered + degraded artifacts.
    created = _http(
        "POST",
        f"{api}/generate",
        {
            "domain": "invoices",
            "count": 2,
            "seed": 4242,
            "provider": "offline",
            "language": "en-IN",
            "render": True,
            "degrade": True,
            "degradation": {"noise": 0.2, "blur": 0.1, "perspective": 0.1, "stamps": 0.15},
        },
    )
    job_id = str(created.get("id") or created.get("job_id") or "")
    assert job_id, ("generate returned no job id", created)

    state = _wait_for_job(api, job_id)
    results = state.get("results") or []
    assert len(results) == 2, ("expected 2 invoice documents", state)

    # 2) The completed invoice job must surface as an OCR ground-truth sample.
    samples = _http("GET", f"{api}/ocr/samples").get("samples", [])
    sample = next((item for item in samples if item.get("job_id") == job_id), None)
    assert sample is not None, ("generated job missing from /ocr/samples", [s.get("job_id") for s in samples])
    assert sample.get("invoice_number"), ("sample missing invoice_number", sample)

    # 3) Score the deterministic noisy demo model against the ground truth.
    report = _http(
        "POST",
        f"{api}/ocr/evaluate",
        {
            "job_id": sample["job_id"],
            "document_index": sample.get("document_index", 0),
            "model_name": "synthetic-ocr-demo",
            "demo_noise": 0.25,
        },
    )
    total = report.get("total_fields", 0)
    correct = report.get("correct_fields", 0)
    accuracy = report.get("accuracy")
    groups = report.get("groups") or {}
    comparisons = report.get("comparisons") or []

    assert total > 0, ("evaluation produced no fields", report)
    assert comparisons, ("evaluation produced no field comparisons", report)
    assert 0 <= correct <= total, ("correct_fields out of range", report)
    assert isinstance(accuracy, (int, float)) and accuracy < 100.0, (
        "noisy demo should score below 100%",
        accuracy,
    )
    assert report.get("incorrect_fields"), ("noisy demo should report incorrect fields", report)
    assert "identity" in groups, ("expected an identity field group", sorted(groups))

    print(
        json.dumps(
            {
                "status": "passed",
                "backend": base,
                "job_id": job_id,
                "documents": len(results),
                "sample_invoice_number": sample.get("invoice_number"),
                "ocr_model": report.get("model"),
                "ocr_accuracy": accuracy,
                "fields_matched": f"{correct}/{total}",
                "group_accuracy": {name: g.get("accuracy") for name, g in groups.items()},
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, KeyError, ValueError, urllib.error.URLError, OSError) as exc:
        print(f"OCR demo smoke failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
