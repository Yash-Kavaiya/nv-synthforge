from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class HRSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_id: int = Field(ge=1)
    title: str = Field(min_length=2)
    body: str = Field(min_length=8)


class HRRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str = Field(pattern=r"^HR-[A-Z0-9-]+$")
    document_type: Literal["offer-letter", "performance-review", "onboarding-checklist"]
    title: str = Field(min_length=4)
    language: Literal["en-IN", "hi-IN", "gu-IN"] = "en-IN"
    employee_id: str = Field(pattern=r"^SYN-EMP-[0-9]+$")
    employee_name: str = Field(min_length=2)
    department: str = Field(min_length=2)
    role_title: str = Field(min_length=2)
    employment_type: Literal["full-time", "contract", "intern"]
    location: str = Field(min_length=2)
    effective_date: date
    annual_ctc_inr: Decimal = Field(gt=0)
    sections: list[HRSection] = Field(min_length=3, max_length=8)
    synthetic: bool = True
    disclaimer: str = "Synthetic HR record. Not an employment contract and not for real personnel decisions."

    @model_validator(mode="after")
    def validate_structure(self) -> "HRRecord":
        if [section.section_id for section in self.sections] != list(range(1, len(self.sections) + 1)):
            raise ValueError("section IDs must be sequential")
        if any(not section.body.strip() for section in self.sections):
            raise ValueError("section bodies must be non-empty")
        return self
