from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel

from app.domain.finance import FinanceStatement
from app.domain.healthcare import MedicalNote
from app.domain.hr import HRRecord
from app.domain.invoice import Invoice, money
from app.domain.legal import LegalContract
from app.domain.retail import RetailProduct
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


def validate_finance_statement(statement: FinanceStatement) -> QualityReport:
    violations: list[Violation] = []
    checks = 5
    if not statement.synthetic or "synthetic" not in statement.disclaimer.lower():
        violations.append(Violation(rule="synthetic_disclaimer", message="finance statement must be marked synthetic"))
    if not statement.entity_id.startswith("SYN-ENT-"):
        violations.append(Violation(rule="pseudonymous_identity", message="entity identifiers must be synthetic"))
    if statement.period_end < statement.period_start:
        violations.append(Violation(rule="period_window", message="period_end must be on or after period_start"))
    debit_sum = sum((item.amount for item in statement.line_items if item.side == "debit"), Decimal("0"))
    credit_sum = sum((item.amount for item in statement.line_items if item.side == "credit"), Decimal("0"))
    if debit_sum != statement.total_debits or credit_sum != statement.total_credits:
        violations.append(Violation(rule="totals", message="posted totals must match line items"))
    if (statement.total_debits - statement.total_credits) != statement.net_position:
        violations.append(Violation(rule="net_position", message="net position must equal debits minus credits"))
    score = max(0.0, round(1.0 - len(violations) / checks, 4))
    return QualityReport(valid=not violations, score=score, violations=violations, rules_checked=checks)


def validate_hr_record(record: HRRecord) -> QualityReport:
    violations: list[Violation] = []
    checks = 5
    if not record.synthetic or "synthetic" not in record.disclaimer.lower():
        violations.append(Violation(rule="synthetic_disclaimer", message="HR record must be marked synthetic"))
    if not record.employee_id.startswith("SYN-EMP-"):
        violations.append(Violation(rule="pseudonymous_identity", message="employee identifiers must be synthetic"))
    if record.annual_ctc_inr <= 0:
        violations.append(Violation(rule="compensation", message="annual CTC must be positive"))
    if len(record.sections) < 3 or [section.section_id for section in record.sections] != list(range(1, len(record.sections) + 1)):
        violations.append(Violation(rule="section_structure", message="HR records require sequential sections"))
    if any(not section.body.strip() for section in record.sections):
        violations.append(Violation(rule="section_content", message="HR sections must include non-empty bodies"))
    score = max(0.0, round(1.0 - len(violations) / checks, 4))
    return QualityReport(valid=not violations, score=score, violations=violations, rules_checked=checks)


def validate_retail_product(product: RetailProduct) -> QualityReport:
    violations: list[Violation] = []
    checks = 5
    if not product.synthetic or "synthetic" not in product.disclaimer.lower():
        violations.append(Violation(rule="synthetic_disclaimer", message="retail product must be marked synthetic"))
    if not product.sku.startswith("SKU-"):
        violations.append(Violation(rule="sku_pattern", message="retail SKUs must use the synthetic SKU pattern"))
    if product.sale_price_inr > product.list_price_inr or product.list_price_inr <= 0:
        violations.append(Violation(rule="pricing", message="sale price must be positive and not exceed list price"))
    if product.review_count != len(product.reviews) or [review.review_id for review in product.reviews] != list(range(1, len(product.reviews) + 1)):
        violations.append(Violation(rule="review_structure", message="reviews must be sequential and match review_count"))
    average = sum(review.rating for review in product.reviews) / max(len(product.reviews), 1)
    if abs(average - product.rating_average) > 0.05:
        violations.append(Violation(rule="rating_average", message="rating average must match review ratings"))
    score = max(0.0, round(1.0 - len(violations) / checks, 4))
    return QualityReport(valid=not violations, score=score, violations=violations, rules_checked=checks)
