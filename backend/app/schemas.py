"""Public request models for the NV-SynthForge HTTP API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.artifacts import DegradationConfig

DomainName = Literal["invoices", "invoice", "healthcare", "support", "legal", "finance", "hr", "retail"]

# Domains whose generator has a NeMo Data Designer adapter. Everything else is offline-only.
NEMO_DOMAINS = frozenset({"invoices", "invoice"})


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


class FinanceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statement_type: Literal["mixed", "balance-sheet", "income-statement", "cash-flow"] = "mixed"
    max_lines: int = Field(default=6, ge=3, le=8)


class HRRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_type: Literal["mixed", "offer-letter", "performance-review", "onboarding-checklist"] = "mixed"
    max_sections: int = Field(default=4, ge=3, le=6)


class RetailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Literal["mixed", "electronics", "home", "apparel", "grocery"] = "mixed"
    max_reviews: int = Field(default=3, ge=1, le=5)


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain: DomainName = "invoices"
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
    finance: FinanceRequest = Field(default_factory=FinanceRequest)
    hr: HRRequest = Field(default_factory=HRRequest)
    retail: RetailRequest = Field(default_factory=RetailRequest)

    @model_validator(mode="after")
    def _provider_supports_domain(self) -> GenerateRequest:
        # Reject up front (422) instead of accepting a job that is guaranteed to fail.
        if self.provider == "nemo" and self.domain not in NEMO_DOMAINS:
            raise ValueError(
                f"NeMo generation is not yet configured for the {self.domain} domain; use provider='offline'"
            )
        return self

    @property
    def canonical_domain(self) -> str:
        return "invoices" if self.domain == "invoice" else self.domain


class BenchmarkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str | None = None
    name: str | None = None


class OCREvalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str | None = None
    document_index: int = Field(default=0, ge=0)
    ground_truth: dict[str, Any] | None = None
    prediction: dict[str, Any] | None = None
    model_name: str = Field(default="user-ocr-model", min_length=1, max_length=128)
    demo_noise: float | None = Field(default=None, ge=0.0, le=0.9)
