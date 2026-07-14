from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


# Fields used for OCR-style structure evaluation against synthetic invoice ground truth.
_SCALAR_PATHS = (
    "invoice_number",
    "invoice_date",
    "currency",
    "place_of_supply",
    "seller.name",
    "seller.gstin",
    "seller.address.line1",
    "seller.address.city",
    "seller.address.state",
    "seller.address.state_code",
    "seller.address.postal_code",
    "buyer.name",
    "buyer.gstin",
    "buyer.address.line1",
    "buyer.address.city",
    "buyer.address.state",
    "buyer.address.state_code",
    "buyer.address.postal_code",
    "subtotal",
    "cgst",
    "sgst",
    "igst",
    "grand_total",
)

_MONEY_PATHS = {
    "subtotal",
    "cgst",
    "sgst",
    "igst",
    "grand_total",
    "items.quantity",
    "items.unit_price",
    "items.gst_rate",
    "items.line_subtotal",
    "items.tax_amount",
    "items.line_total",
}

_ITEM_PATHS = (
    "description",
    "hsn_sac",
    "quantity",
    "unit_price",
    "gst_rate",
    "line_subtotal",
    "tax_amount",
    "line_total",
)


def _dig(source: Any, path: str) -> Any:
    current = source
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _normalize_scalar(path: str, value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return str(value).lower()
    if path in _MONEY_PATHS or path.startswith("items.") and any(path.endswith(suffix) for suffix in ("quantity", "unit_price", "gst_rate", "line_subtotal", "tax_amount", "line_total")):
        try:
            return str(Decimal(str(value).replace(",", "").strip()).quantize(Decimal("0.01")))
        except (InvalidOperation, ValueError, ArithmeticError):
            return str(value).strip()
    text = str(value).strip()
    if path.endswith("gstin"):
        return text.upper()
    if path.endswith("invoice_date"):
        return text[:10]
    return " ".join(text.split())


def _group_for(path: str) -> str:
    if path.startswith("seller.") or path.startswith("buyer."):
        return "parties"
    if path.startswith("items."):
        return "line_items"
    if path in {"subtotal", "cgst", "sgst", "igst", "grand_total"}:
        return "amounts"
    return "identity"


def flatten_invoice_fields(invoice: dict[str, Any]) -> dict[str, str | None]:
    fields: dict[str, str | None] = {}
    for path in _SCALAR_PATHS:
        fields[path] = _normalize_scalar(path, _dig(invoice, path))

    items = invoice.get("items")
    if not isinstance(items, list):
        items = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        for key in _ITEM_PATHS:
            path = f"items[{index}].{key}"
            money_path = f"items.{key}"
            fields[path] = _normalize_scalar(money_path, item.get(key))
    return fields


def evaluate_ocr_prediction(
    *,
    ground_truth: dict[str, Any],
    prediction: dict[str, Any],
    model_name: str = "user-model",
) -> dict[str, Any]:
    """Score OCR/document-understanding output against synthetic invoice ground truth JSON."""
    truth = flatten_invoice_fields(ground_truth)
    pred = flatten_invoice_fields(prediction)

    comparisons: list[dict[str, Any]] = []
    by_group: dict[str, dict[str, int]] = {}

    for path, expected in truth.items():
        actual = pred.get(path)
        matched = expected is not None and actual is not None and expected == actual
        group = "line_items" if path.startswith("items[") else _group_for(path)
        bucket = by_group.setdefault(group, {"total": 0, "correct": 0})
        bucket["total"] += 1
        if matched:
            bucket["correct"] += 1
        comparisons.append(
            {
                "field": path,
                "group": group,
                "expected": expected,
                "predicted": actual,
                "matched": matched,
            }
        )

    total = len(comparisons)
    correct = sum(1 for item in comparisons if item["matched"])
    accuracy = round((correct / total) * 100, 2) if total else 0.0
    groups = {
        name: {
            "total": stats["total"],
            "correct": stats["correct"],
            "accuracy": round((stats["correct"] / stats["total"]) * 100, 2) if stats["total"] else 0.0,
        }
        for name, stats in sorted(by_group.items())
    }

    return {
        "model": model_name,
        "metric_scope": "OCR/document structure accuracy vs synthetic JSON ground truth",
        "total_fields": total,
        "correct_fields": correct,
        "accuracy": accuracy,
        "groups": groups,
        "comparisons": comparisons,
        "missing_fields": [item["field"] for item in comparisons if item["predicted"] is None],
        "incorrect_fields": [item["field"] for item in comparisons if item["predicted"] is not None and not item["matched"]],
    }


def make_noisy_prediction(ground_truth: dict[str, Any], noise_level: float = 0.2) -> dict[str, Any]:
    """Deterministic synthetic OCR prediction with intentional field errors for demos."""
    import copy
    import hashlib
    import json

    prediction = copy.deepcopy(ground_truth)
    blob = json.dumps(ground_truth, sort_keys=True, default=str).encode("utf-8")
    seed = int(hashlib.sha256(blob).hexdigest()[:8], 16)
    fields = list(flatten_invoice_fields(ground_truth).keys())
    error_count = max(1, int(len(fields) * max(0.0, min(noise_level, 0.9))))
    targets = [fields[(seed + i * 7) % len(fields)] for i in range(error_count)]

    def set_path(doc: dict[str, Any], path: str, value: Any) -> None:
        if path.startswith("items["):
            # items[0].description
            left, key = path.split("].", 1)
            index = int(left.split("[", 1)[1])
            items = doc.setdefault("items", [])
            while len(items) <= index:
                items.append({})
            items[index][key] = value
            return
        parts = path.split(".")
        cursor: Any = doc
        for part in parts[:-1]:
            if part not in cursor or not isinstance(cursor[part], dict):
                cursor[part] = {}
            cursor = cursor[part]
        cursor[parts[-1]] = value

    for path in targets:
        if path.endswith("grand_total") or path.endswith("subtotal"):
            set_path(prediction, path, "0.01")
        elif path.endswith("gstin"):
            set_path(prediction, path, "22AAAAA0000A1Z5")
        elif path.endswith("name") or path.endswith("description") or path.endswith("line1") or path.endswith("city"):
            set_path(prediction, path, "OCR_MISREAD")
        elif path.endswith("invoice_number"):
            set_path(prediction, path, f"BAD-{seed % 10000}")
        else:
            set_path(prediction, path, "0")
    return prediction
