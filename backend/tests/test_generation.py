from app.services.generation import OfflineInvoiceGenerator
from app.services.quality import validate_invoice


def test_offline_generation_is_deterministic_and_varied() -> None:
    generator = OfflineInvoiceGenerator()
    first = generator.generate(count=3, seed=42)
    second = generator.generate(count=3, seed=42)
    assert [item.model_dump(mode="json") for item in first] == [item.model_dump(mode="json") for item in second]
    assert len({item.invoice_number for item in first}) == 3


def test_generated_invoice_passes_quality_rules() -> None:
    invoice = OfflineInvoiceGenerator().generate(count=1, seed=7)[0]
    report = validate_invoice(invoice)
    assert report.valid is True
    assert report.score == 1.0
    assert report.violations == []


def test_quality_reports_gstin_state_mismatch() -> None:
    invoice = OfflineInvoiceGenerator().generate(count=1, seed=8)[0]
    invoice.seller.gstin = "27ABCDE1234F1Z5"
    invoice.seller.address.state_code = "29"
    report = validate_invoice(invoice)
    assert report.valid is False
    assert report.score < 1.0
    assert any(item.rule == "gstin_state_code" for item in report.violations)
