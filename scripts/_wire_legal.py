from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "backend" / "app" / "main.py"
text = MAIN.read_text(encoding="utf-8")

replacements = [
    (
        """from app.services.healthcare_generation import OfflineHealthcareGenerator
from app.services.support_generation import OfflineSupportGenerator
from app.services.persistence import SQLiteRepository
from app.services.quality import (
    QualityReport,
    validate_invoice,
    validate_medical_note,
    validate_support_conversation,
)""",
        """from app.services.healthcare_generation import OfflineHealthcareGenerator
from app.services.legal_generation import OfflineLegalGenerator
from app.services.support_generation import OfflineSupportGenerator
from app.services.persistence import SQLiteRepository
from app.services.quality import (
    QualityReport,
    validate_invoice,
    validate_legal_contract,
    validate_medical_note,
    validate_support_conversation,
)""",
    ),
    (
        """class SupportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    industry: Literal["mixed", "telecom", "ecommerce", "banking", "saas"] = "mixed"
    sentiment_arc: Literal["recovery", "steady-positive", "escalation"] = "recovery"
    max_turns: int = Field(default=6, ge=4, le=10)


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain: Literal["invoices", "invoice", "healthcare", "support"] = "invoices"
    count: int = Field(default=1, ge=1, le=100)
    seed: int = Field(default=42, ge=0, le=2_147_483_647)
    provider: Literal["offline", "nemo"] = "offline"
    language: Literal["en-IN", "hi-IN", "gu-IN"] = "en-IN"
    render: bool = True
    degrade: bool = False
    degradation: DegradationRequest = Field(default_factory=DegradationRequest)
    healthcare: HealthcareRequest = Field(default_factory=HealthcareRequest)
    support: SupportRequest = Field(default_factory=SupportRequest)
""",
        """class SupportRequest(BaseModel):
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
""",
    ),
    (
        """        planned = [
            ("legal", "Legal & Contracts", "Agreements, clauses, and compliance records"),
            ("finance", "Finance", "Statements and reconciled financial reports"),
            ("hr", "HR & Recruiting", "Resumes, offers, and performance reviews"),
            ("retail", "Retail", "Products, reviews, and commerce support data"),
        ]""",
        """        planned = [
            ("finance", "Finance", "Statements and reconciled financial reports"),
            ("hr", "HR & Recruiting", "Resumes, offers, and performance reviews"),
            ("retail", "Retail", "Products, reviews, and commerce support data"),
        ]""",
    ),
]

for old, new in replacements:
    if old not in text:
        raise SystemExit(f"missing block:\n{old[:120]}")
    text = text.replace(old, new, 1)

legal_rules = '''

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
'''

if "def _legal_quality_rules" not in text:
    marker = "def _support_quality_rules(report: QualityReport) -> list[dict[str, Any]]:"
    if marker not in text:
        raise SystemExit("support quality rules missing")
    # insert after support quality rules function
    end = text.find("\n\ndef _public_job")
    if end < 0:
        raise SystemExit("public job marker missing")
    text = text[:end] + legal_rules + text[end:]

legal_block = '''
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
'''

if 'if request.domain == "legal":' not in text:
    anchor = '            repository.update_job(job_id, status="running", progress=0.05)\n            if request.domain == "support":'
    if anchor not in text:
        raise SystemExit("generation anchor missing")
    text = text.replace(
        anchor,
        '            repository.update_job(job_id, status="running", progress=0.05)' + legal_block + '\n            if request.domain == "support":',
        1,
    )

MAIN.write_text(text, encoding="utf-8")
print("main.py wired")
