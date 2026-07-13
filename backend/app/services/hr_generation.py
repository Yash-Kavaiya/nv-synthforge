from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from app.domain.hr import HRRecord, HRSection

_TYPES = ("offer-letter", "performance-review", "onboarding-checklist")
_DEPARTMENTS = ("Engineering", "Sales", "People Ops", "Finance", "Support")
_ROLES = {
    "Engineering": ("Backend Engineer", "ML Engineer", "Platform Engineer"),
    "Sales": ("Account Executive", "Solutions Consultant"),
    "People Ops": ("HR Generalist", "Talent Partner"),
    "Finance": ("Financial Analyst", "Controller"),
    "Support": ("Customer Success Manager", "Support Lead"),
}
_LOCATIONS = ("Bengaluru", "Hyderabad", "Pune", "Ahmedabad", "Mumbai")
_SECTIONS = {
    "offer-letter": [
        ("Role summary", "This synthetic offer outlines responsibilities, reporting structure, and expected outcomes for the assigned role."),
        ("Compensation", "Annual CTC, benefits eligibility, and variable pay components are included for synthetic planning scenarios."),
        ("Start date", "Employment is scheduled to begin on the effective date subject to verification workflows."),
        ("Confidentiality", "Candidate and employer details are synthetic and must not be used for real onboarding."),
    ],
    "performance-review": [
        ("Goals", "Review progress against quarterly goals and delivery milestones."),
        ("Strengths", "Document observed strengths across collaboration, ownership, and craft quality."),
        ("Growth areas", "Identify focused growth areas with coaching recommendations."),
        ("Next cycle plan", "Capture agreed actions and measurable outcomes for the next review cycle."),
    ],
    "onboarding-checklist": [
        ("Access provisioning", "Provision identity, tools, and repository access using synthetic credentials."),
        ("Policy acknowledgements", "Capture acknowledgements for code of conduct and information security policies."),
        ("Buddy assignment", "Assign an onboarding buddy and schedule orientation checkpoints."),
        ("Day-30 review", "Schedule a day-30 check-in to validate ramp progress and support needs."),
    ],
}
_LOCALIZED = {
    "en-IN": "",
    "hi-IN": "[हिन्दी एचआर] ",
    "gu-IN": "[ગુજરાતી એચઆર] ",
}


def _money(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class OfflineHRGenerator:
    def generate(
        self,
        count: int,
        seed: int,
        language: str = "en-IN",
        document_type: str = "mixed",
        max_sections: int = 4,
    ) -> list[HRRecord]:
        rng = random.Random(seed)
        records: list[HRRecord] = []
        for index in range(count):
            kind = rng.choice(_TYPES) if document_type == "mixed" else document_type
            if kind not in _TYPES:
                kind = "offer-letter"
            department = rng.choice(_DEPARTMENTS)
            role = rng.choice(_ROLES[department])
            section_templates = _SECTIONS[kind][: max(3, min(max_sections, len(_SECTIONS[kind])))]
            sections = [
                HRSection(
                    section_id=section_id,
                    title=title,
                    body=f"{_LOCALIZED.get(language, '')}{body}",
                )
                for section_id, (title, body) in enumerate(section_templates, start=1)
            ]
            records.append(
                HRRecord(
                    record_id=f"HR-{seed:06d}-{index + 1:04d}",
                    document_type=kind,  # type: ignore[arg-type]
                    title=f"{kind.replace('-', ' ').title()} · {role}",
                    language=language,  # type: ignore[arg-type]
                    employee_id=f"SYN-EMP-{seed % 100000:06d}{(index + 1):02d}",
                    employee_name=f"Employee-{(seed + index) % 9000 + 1000}",
                    department=department,
                    role_title=role,
                    employment_type=rng.choice(("full-time", "contract", "intern")),  # type: ignore[arg-type]
                    location=rng.choice(_LOCATIONS),
                    effective_date=date(2026, 1, 5) + timedelta(days=rng.randint(0, 180)),
                    annual_ctc_inr=_money(rng.uniform(450000, 3200000)),
                    sections=sections,
                    synthetic=True,
                )
            )
        return records
