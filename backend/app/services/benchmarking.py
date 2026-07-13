from __future__ import annotations

from typing import Any


_BENCHMARK_DEFINITIONS = {
    "invoices": {
        "name": "Indian GST invoice quality benchmark",
        "metric_scope": "schema, GST state, subtotal, tax, and grand-total consistency",
    },
    "healthcare": {
        "name": "Clinical note quality benchmark",
        "metric_scope": "synthetic identity, SOAP completeness, ICD-10 diagnosis, and vital-sign consistency",
    },
    "support": {
        "name": "Customer support conversation quality benchmark",
        "metric_scope": "synthetic identity, alternating turns, resolution, and sentiment-arc consistency",
    },
    "legal": {
        "name": "Legal contract quality benchmark",
        "metric_scope": "synthetic parties, clause structure, confidentiality, and disclaimer consistency",
    },
}


def benchmark_for(job: dict[str, Any], name: str | None = None) -> dict[str, Any]:
    documents = job.get("results", [])
    requested_domain = str(job.get("request", {}).get("domain", "invoices"))
    domain = "invoices" if requested_domain == "invoice" else requested_domain
    definition = _BENCHMARK_DEFINITIONS.get(domain, _BENCHMARK_DEFINITIONS["invoices"])
    score = float(job.get("quality_score", 0))
    return {
        "id": f"benchmark-{job['id']}",
        "benchmark_id": f"benchmark-{job['id']}",
        "job_id": job["id"],
        "domain": domain,
        "name": name or definition["name"],
        "score": score,
        "accuracy": score / 100,
        "latency_ms": round(float(job.get("duration_ms", 0)) / max(len(documents), 1), 2),
        "throughput": float(job.get("throughput", 0)),
        "documents": len(documents),
        "created_at": job.get("updated_at"),
        "metric_scope": definition["metric_scope"],
    }
