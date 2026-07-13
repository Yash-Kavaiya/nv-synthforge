from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def wait_for_completion(client: TestClient, job_id: str) -> dict:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        response = client.get(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 200
        job = response.json()
        if job["status"] in {"completed", "failed"}:
            return job
        time.sleep(0.05)
    raise AssertionError("job did not complete")


def test_health_domains_and_openapi(tmp_path: Path) -> None:
    with TestClient(create_app(data_dir=tmp_path)) as client:
        health = client.get("/api/v1/health")
        domains = client.get("/api/v1/domains")
        openapi = client.get("/openapi.json")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert health.json()["nemo_version"] == "0.7.0"
    assert domains.status_code == 200
    assert domains.json()["domains"][0]["id"] == "invoices"
    assert domains.json()["domains"][0]["available"] is True
    assert openapi.status_code == 200


def test_offline_generation_persists_gallery_artifacts_and_benchmark(tmp_path: Path) -> None:
    with TestClient(create_app(data_dir=tmp_path)) as client:
        queued = client.post(
            "/api/v1/generate",
            json={
                "domain": "invoices",
                "count": 2,
                "seed": 77,
                "provider": "offline",
                "language": "hi-IN",
                "render": True,
                "degrade": True,
            },
        )
        assert queued.status_code == 202
        job_id = queued.json()["job_id"]
        job = wait_for_completion(client, job_id)

        assert job["status"] == "completed", job.get("error")
        assert job["progress"] == 100
        assert len(job["results"]) == 2
        assert job["results"][0]["validation_score"] == 100.0
        assert job["results"][0]["language"] == "hi-IN"
        assert job["artifacts"]

        gallery = client.get("/api/v1/gallery")
        assert gallery.status_code == 200
        assert len(gallery.json()["items"]) == 2
        assert gallery.json()["items"][0]["job_id"] == job_id

        benchmark = client.post("/api/v1/benchmarks", json={"job_id": job_id})
        assert benchmark.status_code == 200
        assert benchmark.json()["score"] == 100.0
        assert benchmark.json()["documents"] == 2

        artifact_url = next(item["url"] for item in job["artifacts"] if item["kind"] == "json")
        artifact = client.get(artifact_url)
        assert artifact.status_code == 200
        assert artifact.headers["content-type"].startswith("application/json")

        with client.websocket_connect(f"/api/v1/jobs/{job_id}/ws") as socket:
            event = socket.receive_json()
        assert event["status"] == "completed"
        assert event["progress"] == 100


def test_healthcare_generation_is_available_through_jobs_and_gallery(tmp_path: Path) -> None:
    with TestClient(create_app(data_dir=tmp_path)) as client:
        queued = client.post(
            "/api/v1/generate",
            json={
                "domain": "healthcare",
                "count": 2,
                "seed": 42,
                "provider": "offline",
                "language": "gu-IN",
                "render": False,
                "degrade": False,
                "healthcare": {"clinical_profile": "respiratory", "include_medications": False},
            },
        )
        assert queued.status_code == 202
        job_id = queued.json()["job_id"]
        job = wait_for_completion(client, job_id)

        assert job["status"] == "completed", job.get("error")
        assert len(job["results"]) == 2
        first = job["results"][0]
        assert first["domain"] == "healthcare"
        assert first["medical_note"]["synthetic"] is True
        assert first["medical_note"]["language"] == "gu-IN"
        assert first["medical_note"]["diagnoses"][0]["icd10_code"].startswith("J")
        assert first["medical_note"]["medications"] == []
        assert first["validation_score"] == 100.0
        assert len(first["rules"]) == 5
        assert all(rule["passed"] for rule in first["rules"])

        kinds = {artifact["kind"] for artifact in job["artifacts"]}
        assert {"json", "jsonl"}.issubset(kinds)
        gallery = client.get("/api/v1/gallery").json()["items"]
        assert len(gallery) == 2
        assert all(item["domain"] == "healthcare" for item in gallery)


def test_customer_support_generation_is_available_through_jobs_and_gallery(tmp_path: Path) -> None:
    with TestClient(create_app(data_dir=tmp_path)) as client:
        domains = client.get("/api/v1/domains").json()["domains"]
        support = next(item for item in domains if item["id"] == "support")
        assert support["available"] is True

        queued = client.post(
            "/api/v1/generate",
            json={
                "domain": "support",
                "count": 2,
                "seed": 314,
                "provider": "offline",
                "language": "hi-IN",
                "render": False,
                "degrade": False,
                "support": {
                    "industry": "telecom",
                    "sentiment_arc": "recovery",
                    "max_turns": 6,
                },
            },
        )
        assert queued.status_code == 202
        job = wait_for_completion(client, queued.json()["job_id"])

        assert job["status"] == "completed", job.get("error")
        assert len(job["results"]) == 2
        first = job["results"][0]
        assert first["domain"] == "support"
        assert first["conversation"]["synthetic"] is True
        assert first["conversation"]["industry"] == "telecom"
        assert first["conversation"]["language"] == "hi-IN"
        assert any("\u0900" <= character <= "\u097f" for turn in first["conversation"]["turns"] for character in turn["text"])
        assert first["conversation"]["customer_id"].startswith("SYN-CUST-")
        assert 4 <= len(first["conversation"]["turns"]) <= 6
        assert first["conversation"]["turns"][0]["role"] == "customer"
        assert first["conversation"]["turns"][-1]["role"] == "agent"
        assert first["validation_score"] == 100.0
        assert len(first["rules"]) == 5
        assert all(rule["passed"] for rule in first["rules"])
        assert {artifact["kind"] for artifact in job["artifacts"]} >= {"json", "jsonl"}
        assert client.get("/api/v1/gallery").json()["items"][0]["domain"] == "support"


def test_legal_generation_is_available_through_jobs_and_gallery(tmp_path: Path) -> None:
    with TestClient(create_app(data_dir=tmp_path)) as client:
        domains = client.get("/api/v1/domains").json()["domains"]
        legal = next(item for item in domains if item["id"] == "legal")
        assert legal["available"] is True

        queued = client.post(
            "/api/v1/generate",
            json={
                "domain": "legal",
                "count": 2,
                "seed": 77,
                "provider": "offline",
                "language": "gu-IN",
                "render": False,
                "degrade": False,
                "legal": {"document_type": "nda", "max_clauses": 5},
            },
        )
        assert queued.status_code == 202
        job = wait_for_completion(client, queued.json()["job_id"])

        assert job["status"] == "completed", job.get("error")
        assert len(job["results"]) == 2
        first = job["results"][0]
        assert first["domain"] == "legal"
        assert first["contract"]["synthetic"] is True
        assert first["contract"]["document_type"] == "nda"
        assert first["contract"]["language"] == "gu-IN"
        assert first["contract"]["contract_id"].startswith("LEG-")
        assert all(party["party_id"].startswith("SYN-PARTY-") for party in first["contract"]["parties"])
        assert len(first["contract"]["clauses"]) == 5
        assert any("\u0a80" <= character <= "\u0aff" for character in first["contract"]["clauses"][0]["body"])
        assert first["validation_score"] == 100.0
        assert len(first["rules"]) == 5
        assert all(rule["passed"] for rule in first["rules"])
        assert {artifact["kind"] for artifact in job["artifacts"]} >= {"json", "jsonl"}
        assert client.get("/api/v1/gallery").json()["items"][0]["domain"] == "legal"


def test_benchmarks_report_domain_specific_metric_scopes(tmp_path: Path) -> None:
    with TestClient(create_app(data_dir=tmp_path)) as client:
        job_ids: dict[str, str] = {}
        for domain in ("invoices", "support", "healthcare", "legal"):
            queued = client.post(
                "/api/v1/generate",
                json={
                    "domain": domain,
                    "count": 1,
                    "seed": 91,
                    "provider": "offline",
                    "render": False,
                    "degrade": False,
                },
            )
            assert queued.status_code == 202
            job = wait_for_completion(client, queued.json()["job_id"])
            assert job["status"] == "completed", job.get("error")
            job_ids[domain] = job["job_id"]

        benchmarks = client.get("/api/v1/benchmarks").json()["benchmarks"]
        by_domain = {benchmark["domain"]: benchmark for benchmark in benchmarks}
        assert set(by_domain) == {"invoices", "support", "healthcare", "legal"}
        assert "GST" in by_domain["invoices"]["metric_scope"]
        assert "SOAP" in by_domain["healthcare"]["metric_scope"]
        assert "sentiment" in by_domain["support"]["metric_scope"]
        assert "clause" in by_domain["legal"]["metric_scope"]
        assert by_domain["support"]["name"] == "Customer support conversation quality benchmark"
        assert by_domain["legal"]["name"] == "Legal contract quality benchmark"

        support_benchmark = client.post(
            "/api/v1/benchmarks",
            json={"job_id": job_ids["support"]},
        )
        assert support_benchmark.status_code == 200
        assert support_benchmark.json()["domain"] == "support"
        assert support_benchmark.json()["score"] == 100.0

        legal_benchmark = client.post(
            "/api/v1/benchmarks",
            json={"job_id": job_ids["legal"]},
        )
        assert legal_benchmark.status_code == 200
        assert legal_benchmark.json()["domain"] == "legal"
        assert legal_benchmark.json()["score"] == 100.0


def test_generation_is_deterministic_and_nemo_missing_key_is_clear(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    with TestClient(create_app(data_dir=tmp_path)) as client:
        payload = {"domain": "invoices", "count": 1, "seed": 19, "provider": "offline", "render": False}
        first = client.post("/api/v1/generate", json=payload)
        second = client.post("/api/v1/generate", json=payload)
        first_job = wait_for_completion(client, first.json()["job_id"])
        second_job = wait_for_completion(client, second.json()["job_id"])
        assert first_job["results"][0]["invoice"] == second_job["results"][0]["invoice"]

        nemo = client.post("/api/v1/generate", json={**payload, "provider": "nemo"})
        nemo_job = wait_for_completion(client, nemo.json()["job_id"])
        assert nemo_job["status"] == "failed"
        assert "NVIDIA_API_KEY" in nemo_job["error"]


def test_validation_and_not_found_errors(tmp_path: Path) -> None:
    with TestClient(create_app(data_dir=tmp_path)) as client:
        assert client.post("/api/v1/generate", json={"domain": "unknown", "count": 1}).status_code == 422
        assert client.post("/api/v1/generate", json={"domain": "invoices", "count": 0}).status_code == 422
        assert client.get("/api/v1/jobs/missing").status_code == 404
