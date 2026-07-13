from __future__ import annotations

import random
from datetime import date, timedelta

from app.domain.legal import ContractClause, LegalContract, LegalParty

_TEMPLATES = {
    "nda": {
        "title": "Mutual Non-Disclosure Agreement",
        "roles": ("disclosing_party", "receiving_party"),
        "clauses": [
            ("Purpose", "The parties may share confidential information solely to evaluate a potential collaboration."),
            ("Confidential Information", "Confidential information includes technical, commercial, and customer data marked or reasonably understood as confidential."),
            ("Non-Use", "The receiving party shall not use confidential information for any purpose other than the stated evaluation."),
            ("Non-Disclosure", "The receiving party shall protect confidential information with reasonable care and limit access to need-to-know personnel."),
            ("Term", "Confidentiality obligations survive termination for the residual term specified in this agreement."),
            ("Return or Destruction", "Upon request, the receiving party shall return or securely destroy confidential materials except retained legal archives."),
            ("No License", "No intellectual-property license is granted except the limited evaluation right stated herein."),
            ("Remedies", "Unauthorized disclosure may cause irreparable harm and may justify injunctive relief in addition to other remedies."),
        ],
    },
    "service-agreement": {
        "title": "Professional Services Agreement",
        "roles": ("service_provider", "customer"),
        "clauses": [
            ("Services", "The provider shall deliver the scoped professional services described in the attached statement of work."),
            ("Fees", "Fees are payable according to the schedule in the statement of work and exclude applicable taxes."),
            ("Acceptance", "Deliverables are accepted when the customer confirms completion or fails to raise material defects within the review window."),
            ("Change Control", "Material scope changes require written change orders with adjusted fees and timelines."),
            ("Confidentiality", "Each party shall protect the other party's non-public information using commercially reasonable safeguards."),
            ("IP Ownership", "Pre-existing IP remains with its owner; newly created work product is assigned as stated in the statement of work."),
            ("Limitation of Liability", "Except for willful misconduct, aggregate liability is limited to fees paid under the relevant statement of work."),
            ("Termination", "Either party may terminate for material breach that remains uncured after written notice."),
        ],
    },
    "msa": {
        "title": "Master Services Agreement",
        "roles": ("service_provider", "customer"),
        "clauses": [
            ("Framework", "This master agreement governs statements of work issued during the term."),
            ("Ordering", "Each statement of work becomes binding when signed by authorized representatives of both parties."),
            ("Service Levels", "Service levels, credits, and exclusions are defined in the applicable statement of work or annex."),
            ("Data Protection", "Personal data processing follows the data-processing terms and applicable Indian privacy requirements."),
            ("Subcontracting", "The provider remains responsible for subcontractors performing under this agreement."),
            ("Audit", "The customer may request reasonable audit evidence of security and compliance controls once per year."),
            ("Indemnity", "Each party indemnifies the other against third-party claims arising from its material breach or negligence."),
            ("Governing Hierarchy", "If a statement of work conflicts with this master agreement, the master agreement controls unless the statement of work expressly overrides a clause."),
        ],
    },
}

_PARTY_NAMES = (
    "Nova Analytics Pvt Ltd",
    "Indigo Systems LLP",
    "Harbor Retail India Pvt Ltd",
    "Cedar Cloud Services Ltd",
    "Orbit Finance Technologies Pvt Ltd",
    "Saffron Logistics LLP",
)

_LAWS = (
    "Laws of India",
    "Laws of Maharashtra",
    "Laws of Karnataka",
    "Laws of Delhi",
    "Laws of Gujarat",
    "Laws of Tamil Nadu",
)

_LOCALIZED_PREFIX = {
    "en-IN": "",
    "hi-IN": "[हिन्दी अनुबंध] ",
    "gu-IN": "[ગુજરાતી કરાર] ",
}


class OfflineLegalGenerator:
    def generate(
        self,
        count: int,
        seed: int,
        language: str = "en-IN",
        document_type: str = "mixed",
        max_clauses: int = 6,
    ) -> list[LegalContract]:
        if not 1 <= count <= 10_000:
            raise ValueError("count must be between 1 and 10000")
        if document_type not in {*_TEMPLATES, "mixed"}:
            raise ValueError("unsupported legal document type")
        if not 3 <= max_clauses <= 8:
            raise ValueError("max_clauses must be between 3 and 8")

        rng = random.Random(seed)
        types = list(_TEMPLATES) if document_type == "mixed" else [document_type]
        prefix = _LOCALIZED_PREFIX.get(language, "")
        results: list[LegalContract] = []

        for index in range(1, count + 1):
            selected_type = rng.choice(types)
            template = _TEMPLATES[selected_type]
            role_a, role_b = template["roles"]
            name_a, name_b = rng.sample(_PARTY_NAMES, 2)
            clause_count = min(max_clauses, len(template["clauses"]))
            selected_clauses = template["clauses"][:clause_count]
            risk_cycle = ("none", "none", "medium", "none", "high", "none", "medium", "none")
            clauses = [
                ContractClause(
                    clause_id=clause_index,
                    title=title,
                    body=f"{prefix}{body}" if clause_index == 1 and prefix else body,
                    risk_flag=risk_cycle[(clause_index - 1) % len(risk_cycle)],
                )
                for clause_index, (title, body) in enumerate(selected_clauses, start=1)
            ]
            results.append(
                LegalContract(
                    contract_id=f"LEG-{seed:06d}-{index:04d}",
                    document_type=selected_type,  # type: ignore[arg-type]
                    title=template["title"],
                    language=language,  # type: ignore[arg-type]
                    effective_date=date(2026, 1, 1) + timedelta(days=rng.randrange(300)),
                    term_months=rng.choice([6, 12, 18, 24, 36]),
                    governing_law=rng.choice(_LAWS),
                    parties=[
                        LegalParty(
                            party_id=f"SYN-PARTY-{(seed * 53 + index) % 900000 + 100000}",
                            name=name_a,
                            role=role_a,  # type: ignore[arg-type]
                            jurisdiction="India",
                        ),
                        LegalParty(
                            party_id=f"SYN-PARTY-{(seed * 71 + index) % 900000 + 200000}",
                            name=name_b,
                            role=role_b,  # type: ignore[arg-type]
                            jurisdiction="India",
                        ),
                    ],
                    clauses=clauses,
                    confidentiality=True,
                )
            )
        return results
