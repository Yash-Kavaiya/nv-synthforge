from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel

from app.domain.healthcare import MedicalNote
from app.domain.invoice import Invoice, money
from app.domain.legal import LegalContract
from app.domain.support import SupportConversation


class Violation(BaseModel):
    rule: str
    message: str
    severity: str = "error"


class QualityReport(BaseModel):
    valid: bool
    score: float
    violations: list[Violation]
    rules_checked: int


def validate_invoice(invoice: Invoice) -> QualityReport:
    violations: list[Violation] = []
    checks = 5
    for role, party in (("seller", invoice.seller), ("buyer", invoice.buyer)):
        if party.gstin[:2] != party.address.state_code:
            violations.append(Violation(rule="gstin_state_code", message=f"{role} GSTIN prefix must match address state code"))
    subtotal = money(sum((item.line_subtotal for item in invoice.items), Decimal("0")))
    tax = money(sum((item.tax_amount for item in invoice.items), Decimal("0")))
    if invoice.subtotal != subtotal:
        violations.append(Violation(rule="subtotal", message="subtotal does not equal item subtotal sum"))
    if money(invoice.cgst + invoice.sgst + invoice.igst) != tax:
        violations.append(Violation(rule="tax_total", message="GST components do not equal item tax sum"))
    if invoice.grand_total != money(subtotal + tax):
        violations.append(Violation(rule="grand_total", message="grand total is inconsistent"))
    score = max(0.0, round(1.0 - len(violations) / checks, 4))
    return QualityReport(valid=not violations, score=score, violations=violations, rules_checked=checks)


def validate_medical_note(note: MedicalNote) -> QualityReport:
    violations: list[Violation] = []
    checks = 5
    if not note.synthetic or "Synthetic clinical record" not in note.disclaimer:
        violations.append(Violation(rule="synthetic_disclaimer", message="record must be explicitly marked synthetic"))
    if not note.patient.patient_id.startswith("SYN-PAT-") or not note.patient.name.startswith("Patient-"):
        violations.append(Violation(rule="pseudonymous_identity", message="patient identity must use synthetic identifiers"))
    if not all((note.soap.subjective, note.soap.objective, note.soap.assessment, note.soap.plan)):
        violations.append(Violation(rule="soap_completeness", message="all SOAP sections are required"))
    if not note.diagnoses:
        violations.append(Violation(rule="diagnosis", message="at least one ICD-10 diagnosis is required"))
    if note.vitals.systolic_mm_hg <= note.vitals.diastolic_mm_hg:
        violations.append(Violation(rule="vitals", message="systolic pressure must exceed diastolic pressure"))
    score = max(0.0, round(1.0 - len(violations) / checks, 4))
    return QualityReport(valid=not violations, score=score, violations=violations, rules_checked=checks)


def validate_support_conversation(conversation: SupportConversation) -> QualityReport:
    violations: list[Violation] = []
    checks = 5
    if not conversation.synthetic or "Synthetic customer-support conversation" not in conversation.disclaimer:
        violations.append(Violation(rule="synthetic_disclaimer", message="conversation must be explicitly marked synthetic"))
    if not conversation.customer_id.startswith("SYN-CUST-"):
        violations.append(Violation(rule="pseudonymous_identity", message="customer must use a synthetic identifier"))
    if conversation.turns[0].role != "customer" or any(
        left.role == right.role for left, right in zip(conversation.turns, conversation.turns[1:])
    ):
        violations.append(Violation(rule="turn_structure", message="turns must start with a customer and alternate roles"))
    closing_turn = conversation.turns[-1]
    if conversation.resolution_status == "resolved" and (
        closing_turn.role != "agent" or closing_turn.sentiment < 0.5
    ):
        violations.append(Violation(rule="resolution", message="resolved conversations require a positive closing agent turn"))
    elif conversation.resolution_status == "escalated" and (
        closing_turn.role != "agent" or closing_turn.sentiment >= 0
    ):
        violations.append(Violation(rule="resolution", message="escalated conversations require a negative closing agent turn"))
    first_sentiment = conversation.turns[0].sentiment
    last_sentiment = conversation.turns[-1].sentiment
    arc_valid = {
        "recovery": last_sentiment > first_sentiment,
        "steady-positive": last_sentiment >= first_sentiment,
        "escalation": last_sentiment < first_sentiment,
    }[conversation.sentiment_arc]
    if not arc_valid:
        violations.append(Violation(rule="sentiment_arc", message="turn sentiment does not match the configured arc"))
    score = max(0.0, round(1.0 - len(violations) / checks, 4))
    return QualityReport(valid=not violations, score=score, violations=violations, rules_checked=checks)


def validate_legal_contract(contract: LegalContract) -> QualityReport:
    violations: list[Violation] = []
    checks = 5
    if not contract.synthetic or "Synthetic legal contract" not in contract.disclaimer:
        violations.append(Violation(rule="synthetic_disclaimer", message="contract must be explicitly marked synthetic"))
    if any(not party.party_id.startswith("SYN-PARTY-") for party in contract.parties):
        violations.append(Violation(rule="pseudonymous_identity", message="parties must use synthetic identifiers"))
    if len({party.party_id for party in contract.parties}) != len(contract.parties):
        violations.append(Violation(rule="party_distinctness", message="contract parties must be distinct"))
    if len(contract.clauses) < 3 or [clause.clause_id for clause in contract.clauses] != list(range(1, len(contract.clauses) + 1)):
        violations.append(Violation(rule="clause_structure", message="contracts require sequential clauses"))
    if not contract.confidentiality:
        violations.append(Violation(rule="confidentiality", message="generated contracts must include confidentiality coverage"))
    score = max(0.0, round(1.0 - len(violations) / checks, 4))
    return QualityReport(valid=not violations, score=score, violations=violations, rules_checked=checks)
