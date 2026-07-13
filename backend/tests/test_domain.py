from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.domain.invoice import Address, Invoice, InvoiceItem, Party
from app.domain.registry import get_domain, list_domains


def make_invoice() -> Invoice:
    return Invoice(
        invoice_number="INV-2026-0001",
        invoice_date="2026-07-13",
        seller=Party(
            name="SynthForge Systems Pvt Ltd",
            gstin="27ABCDE1234F1Z5",
            address=Address(line1="BKC", city="Mumbai", state="Maharashtra", state_code="27", postal_code="400051"),
        ),
        buyer=Party(
            name="Acme Retail Pvt Ltd",
            gstin="29ABCDE1234F1Z3",
            address=Address(line1="MG Road", city="Bengaluru", state="Karnataka", state_code="29", postal_code="560001"),
        ),
        items=[InvoiceItem(description="GPU compute services", hsn_sac="998314", quantity=2, unit_price="1000.00", gst_rate="18")],
    )


def test_invoice_computes_interstate_igst_totals() -> None:
    invoice = make_invoice()
    assert invoice.subtotal == Decimal("2000.00")
    assert invoice.cgst == Decimal("0.00")
    assert invoice.sgst == Decimal("0.00")
    assert invoice.igst == Decimal("360.00")
    assert invoice.grand_total == Decimal("2360.00")


def test_invoice_rejects_invalid_gstin_checksum_shape() -> None:
    with pytest.raises(ValidationError):
        Party(
            name="Bad GST",
            gstin="INVALID",
            address=Address(line1="X", city="Mumbai", state="Maharashtra", state_code="27", postal_code="400001"),
        )


def test_domain_registry_exposes_available_capabilities() -> None:
    domains = list_domains()
    assert [domain.slug for domain in domains] == ["invoice", "healthcare", "support", "legal"]
    assert get_domain("invoice").supports == {"json", "document", "image"}
    assert get_domain("healthcare").supports == {"json"}
    assert get_domain("support").supports == {"json"}
    assert get_domain("legal").supports == {"json"}
