from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from app.domain.finance import FinanceLineItem, FinanceStatement

_TYPES = ("balance-sheet", "income-statement", "cash-flow")
_ENTITIES = (
    "Nova Ledger Labs Pvt Ltd",
    "Indigo Cashworks LLP",
    "Saffron Capital Desk",
    "Orbit Treasury Systems",
)
_ACCOUNTS = {
    "balance-sheet": [
        ("1000", "Cash and equivalents", "debit"),
        ("1200", "Accounts receivable", "debit"),
        ("1500", "Inventory", "debit"),
        ("2000", "Accounts payable", "credit"),
        ("2100", "Short-term debt", "credit"),
        ("3000", "Retained earnings", "credit"),
    ],
    "income-statement": [
        ("4000", "Product revenue", "credit"),
        ("4100", "Service revenue", "credit"),
        ("5000", "Cost of goods sold", "debit"),
        ("5100", "Operating expenses", "debit"),
        ("5200", "Depreciation", "debit"),
        ("6000", "Tax expense", "debit"),
    ],
    "cash-flow": [
        ("7000", "Cash from operations", "debit"),
        ("7100", "Cash from investing", "credit"),
        ("7200", "Cash from financing", "debit"),
        ("7300", "Working capital changes", "credit"),
        ("7400", "Capex outflows", "credit"),
        ("7500", "Net cash movement", "debit"),
    ],
}
_LOCALIZED = {
    "en-IN": "",
    "hi-IN": "[हिन्दी वित्त] ",
    "gu-IN": "[ગુજરાતી ફાઇનાન્સ] ",
}


def _money(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class OfflineFinanceGenerator:
    def generate(
        self,
        count: int,
        seed: int,
        language: str = "en-IN",
        statement_type: str = "mixed",
        max_lines: int = 6,
    ) -> list[FinanceStatement]:
        rng = random.Random(seed)
        records: list[FinanceStatement] = []
        for index in range(count):
            kind = (
                rng.choice(_TYPES)
                if statement_type == "mixed"
                else statement_type  # type: ignore[assignment]
            )
            if kind not in _TYPES:
                kind = "income-statement"
            accounts = _ACCOUNTS[kind][: max(3, min(max_lines, len(_ACCOUNTS[kind])))]
            line_items: list[FinanceLineItem] = []
            for line_id, (code, label, side) in enumerate(accounts, start=1):
                amount = _money(rng.uniform(1200, 85000))
                line_items.append(
                    FinanceLineItem(
                        line_id=line_id,
                        account_code=code,
                        label=f"{_LOCALIZED.get(language, '')}{label}",
                        amount=amount,
                        side=side,  # type: ignore[arg-type]
                    )
                )
            total_debits = sum((item.amount for item in line_items if item.side == "debit"), Decimal("0"))
            total_credits = sum((item.amount for item in line_items if item.side == "credit"), Decimal("0"))
            period_end = date(2026, 1, 1) + timedelta(days=rng.randint(0, 200))
            period_start = period_end - timedelta(days=rng.choice([30, 90, 180, 365]))
            entity_name = rng.choice(_ENTITIES)
            records.append(
                FinanceStatement(
                    statement_id=f"FIN-{seed:06d}-{index + 1:04d}",
                    statement_type=kind,  # type: ignore[arg-type]
                    title=f"{kind.replace('-', ' ').title()} · {entity_name}",
                    language=language,  # type: ignore[arg-type]
                    entity_id=f"SYN-ENT-{seed % 100000:06d}{(index + 1):02d}",
                    entity_name=entity_name,
                    period_start=period_start,
                    period_end=period_end,
                    currency="INR",
                    line_items=line_items,
                    total_debits=total_debits,
                    total_credits=total_credits,
                    net_position=total_debits - total_credits,
                    synthetic=True,
                )
            )
        return records
