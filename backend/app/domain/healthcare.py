from __future__ import annotations

import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

ICD10_RE = re.compile(r"^[A-Z][0-9]{2}(?:\.[0-9A-Z]{1,4})?$")


class SyntheticPatient(BaseModel):
    patient_id: str = Field(pattern=r"^SYN-PAT-[0-9]{6}$")
    name: str = Field(pattern=r"^Patient-[0-9]{4}$")
    age: int = Field(ge=0, le=120)
    gender: Literal["female", "male", "non-binary", "not-disclosed"]


class VitalSigns(BaseModel):
    temperature_c: float = Field(ge=30, le=45)
    pulse_bpm: int = Field(ge=20, le=250)
    systolic_mm_hg: int = Field(ge=50, le=260)
    diastolic_mm_hg: int = Field(ge=30, le=160)
    spo2_percent: int = Field(ge=50, le=100)

    @model_validator(mode="after")
    def pressure_is_ordered(self) -> VitalSigns:
        if self.systolic_mm_hg <= self.diastolic_mm_hg:
            raise ValueError("systolic pressure must exceed diastolic pressure")
        return self


class Diagnosis(BaseModel):
    icd10_code: str
    description: str = Field(min_length=3)

    @field_validator("icd10_code")
    @classmethod
    def valid_icd10(cls, value: str) -> str:
        code = value.strip().upper()
        if not ICD10_RE.fullmatch(code):
            raise ValueError("invalid ICD-10 code shape")
        return code


class Medication(BaseModel):
    generic_name: str = Field(min_length=2)
    dose: str = Field(min_length=1)
    route: Literal["oral", "topical", "inhaled", "intravenous", "subcutaneous"]
    frequency: str = Field(min_length=2)
    duration_days: int | None = Field(default=None, ge=1, le=365)


class SOAPNote(BaseModel):
    subjective: str = Field(min_length=10)
    objective: str = Field(min_length=10)
    assessment: str = Field(min_length=5)
    plan: str = Field(min_length=10)


class MedicalNote(BaseModel):
    note_id: str = Field(pattern=r"^MED-[0-9]{6}-[0-9]{4}$")
    encounter_date: date
    language: Literal["en-IN", "hi-IN", "gu-IN"] = "en-IN"
    patient: SyntheticPatient
    chief_complaint: str = Field(min_length=3)
    vitals: VitalSigns
    soap: SOAPNote
    diagnoses: list[Diagnosis] = Field(min_length=1, max_length=8)
    medications: list[Medication] = Field(default_factory=list, max_length=20)
    redaction_markers: list[str] = Field(default_factory=lambda: ["[REDACTED_CONTACT]"])
    synthetic: Literal[True] = True
    disclaimer: str = "Synthetic clinical record. Not for patient care."
