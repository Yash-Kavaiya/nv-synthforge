from app.services.finance_generation import OfflineFinanceGenerator
from app.services.hr_generation import OfflineHRGenerator
from app.services.quality import validate_finance_statement, validate_hr_record, validate_retail_product
from app.services.retail_generation import OfflineRetailGenerator


def test_finance_generation_is_deterministic_and_valid() -> None:
    left = OfflineFinanceGenerator().generate(2, 42, language="hi-IN", statement_type="balance-sheet", max_lines=5)
    right = OfflineFinanceGenerator().generate(2, 42, language="hi-IN", statement_type="balance-sheet", max_lines=5)
    assert [item.model_dump(mode="json") for item in left] == [item.model_dump(mode="json") for item in right]
    assert left[0].statement_type == "balance-sheet"
    assert left[0].entity_id.startswith("SYN-ENT-")
    assert all(validate_finance_statement(item).valid for item in left)
    assert any("\u0900" <= ch <= "\u097f" for ch in left[0].line_items[0].label)


def test_hr_generation_is_deterministic_and_valid() -> None:
    left = OfflineHRGenerator().generate(2, 51, language="gu-IN", document_type="offer-letter", max_sections=4)
    right = OfflineHRGenerator().generate(2, 51, language="gu-IN", document_type="offer-letter", max_sections=4)
    assert [item.model_dump(mode="json") for item in left] == [item.model_dump(mode="json") for item in right]
    assert left[0].document_type == "offer-letter"
    assert left[0].employee_id.startswith("SYN-EMP-")
    assert all(validate_hr_record(item).valid for item in left)
    assert any("\u0a80" <= ch <= "\u0aff" for ch in left[0].sections[0].body)


def test_retail_generation_is_deterministic_and_valid() -> None:
    left = OfflineRetailGenerator().generate(2, 88, language="en-IN", category="electronics", max_reviews=3)
    right = OfflineRetailGenerator().generate(2, 88, language="en-IN", category="electronics", max_reviews=3)
    assert [item.model_dump(mode="json") for item in left] == [item.model_dump(mode="json") for item in right]
    assert left[0].category == "electronics"
    assert left[0].sku.startswith("SKU-")
    assert all(validate_retail_product(item).valid for item in left)
