from __future__ import annotations

import random
from datetime import date, timedelta

from app.domain.healthcare import Diagnosis, MedicalNote, Medication, SOAPNote, SyntheticPatient, VitalSigns

_SCENARIOS = [
    {
        "profile": "respiratory",
        "chief": "Fever and dry cough for three days",
        "subjective": "Patient reports low-grade fever, dry cough, fatigue, and reduced appetite for three days.",
        "objective": "Mild pharyngeal erythema without respiratory distress; lungs clear on auscultation.",
        "assessment": "Acute viral upper respiratory infection without red-flag symptoms.",
        "plan": "Supportive care, oral fluids, rest, temperature monitoring, and review if symptoms worsen.",
        "diagnosis": ("J06.9", "Acute upper respiratory infection, unspecified"),
        "medication": ("Paracetamol", "500 mg", "oral", "as needed up to three times daily", 3),
    },
    {
        "profile": "cardiovascular",
        "chief": "Elevated blood pressure during routine review",
        "subjective": "Patient is asymptomatic and reports inconsistent home blood-pressure monitoring.",
        "objective": "Repeat seated blood pressure remains elevated; cardiovascular examination otherwise unremarkable.",
        "assessment": "Essential hypertension requiring adherence and lifestyle review.",
        "plan": "Continue treatment, reduce dietary sodium, maintain home readings, and follow up in four weeks.",
        "diagnosis": ("I10", "Essential hypertension"),
        "medication": ("Amlodipine", "5 mg", "oral", "once daily", 30),
    },
    {
        "profile": "general",
        "chief": "Burning upper abdominal discomfort after meals",
        "subjective": "Patient reports intermittent epigastric burning and sour belching, worse after spicy meals.",
        "objective": "Abdomen soft with mild epigastric tenderness and no guarding or palpable mass.",
        "assessment": "Dyspepsia without current alarm features.",
        "plan": "Trial acid suppression, smaller meals, avoid trigger foods, and reassess in two weeks.",
        "diagnosis": ("K30", "Functional dyspepsia"),
        "medication": ("Pantoprazole", "40 mg", "oral", "once daily before breakfast", 14),
    },
    {
        "profile": "general",
        "chief": "Itchy rash over both forearms",
        "subjective": "Patient noticed an itchy rash after using a new household cleaning product.",
        "objective": "Symmetric erythematous patches over forearms without blistering or mucosal involvement.",
        "assessment": "Likely irritant contact dermatitis with no evidence of secondary infection.",
        "plan": "Avoid suspected irritant, use emollient, apply topical treatment, and return for spreading rash.",
        "diagnosis": ("L24.9", "Irritant contact dermatitis, unspecified cause"),
        "medication": ("Hydrocortisone", "1% thin layer", "topical", "twice daily", 7),
    },
]
_GENDERS = ["female", "male", "non-binary", "not-disclosed"]


class OfflineHealthcareGenerator:
    """Seeded generator for privacy-safe, non-clinical SOAP records."""

    def generate(
        self,
        count: int,
        seed: int,
        language: str = "en-IN",
        clinical_profile: str = "mixed",
        include_medications: bool = True,
    ) -> list[MedicalNote]:
        if not 1 <= count <= 10_000:
            raise ValueError("count must be between 1 and 10000")
        if clinical_profile not in {"mixed", "respiratory", "cardiovascular", "general"}:
            raise ValueError("unsupported clinical profile")
        scenarios = _SCENARIOS if clinical_profile == "mixed" else [scenario for scenario in _SCENARIOS if scenario["profile"] == clinical_profile]
        rng = random.Random(seed)
        records: list[MedicalNote] = []
        for index in range(count):
            scenario = rng.choice(scenarios)
            systolic = rng.randint(104, 154)
            diastolic = rng.randint(64, min(98, systolic - 10))
            diagnosis_code, diagnosis_name = scenario["diagnosis"]
            generic_name, dose, route, frequency, duration = scenario["medication"]
            records.append(
                MedicalNote(
                    note_id=f"MED-{seed:06d}-{index + 1:04d}",
                    encounter_date=date(2026, 1, 1) + timedelta(days=rng.randint(0, 364)),
                    language=language,
                    patient=SyntheticPatient(
                        patient_id=f"SYN-PAT-{(seed * 997 + index) % 1_000_000:06d}",
                        name=f"Patient-{(seed * 37 + index) % 10_000:04d}",
                        age=rng.randint(18, 85),
                        gender=rng.choice(_GENDERS),
                    ),
                    chief_complaint=scenario["chief"],
                    vitals=VitalSigns(
                        temperature_c=round(rng.uniform(36.2, 38.8), 1),
                        pulse_bpm=rng.randint(62, 108),
                        systolic_mm_hg=systolic,
                        diastolic_mm_hg=diastolic,
                        spo2_percent=rng.randint(94, 100),
                    ),
                    soap=SOAPNote(
                        subjective=scenario["subjective"],
                        objective=scenario["objective"],
                        assessment=scenario["assessment"],
                        plan=scenario["plan"],
                    ),
                    diagnoses=[Diagnosis(icd10_code=diagnosis_code, description=diagnosis_name)],
                    medications=[
                        Medication(
                            generic_name=generic_name,
                            dose=dose,
                            route=route,
                            frequency=frequency,
                            duration_days=duration,
                        )
                    ] if include_medications else [],
                )
            )
        return records
