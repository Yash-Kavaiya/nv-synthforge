from dataclasses import dataclass


@dataclass(frozen=True)
class DomainDefinition:
    slug: str
    name: str
    description: str
    supports: set[str]


_DOMAINS = {
    "invoice": DomainDefinition(
        slug="invoice",
        name="Indian GST Invoice",
        description="Deterministic GST-compliant invoice records and rendered documents.",
        supports={"json", "document", "image"},
    ),
    "healthcare": DomainDefinition(
        slug="healthcare",
        name="Synthetic Clinical Notes",
        description="Privacy-safe SOAP notes with ICD-10 diagnoses, medication data, and clinical consistency checks.",
        supports={"json"},
    ),
    "support": DomainDefinition(
        slug="support",
        name="Customer Support Conversations",
        description="Multi-turn service interactions with configurable industries, sentiment arcs, and resolution checks.",
        supports={"json"},
    ),
    "legal": DomainDefinition(
        slug="legal",
        name="Legal & Contracts",
        description="NDAs, service agreements, and MSAs with clause libraries, risk flags, and synthetic party identifiers.",
        supports={"json"},
    ),
}


def list_domains() -> list[DomainDefinition]:
    return list(_DOMAINS.values())


def get_domain(slug: str) -> DomainDefinition:
    try:
        return _DOMAINS[slug]
    except KeyError as exc:
        raise KeyError(f"Unknown domain: {slug}") from exc
