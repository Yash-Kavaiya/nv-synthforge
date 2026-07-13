from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FinanceLineItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    line_id: int = Field(ge=1)
    account_code: str = Field(min_length=3)
    label: str = Field(min_length=2)
    amount: Decimal
    side: Literal["debit", "credit"]


class FinanceStatement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statement_id: str = Field(pattern=r"^FIN-[A-Z0-9-]+$")
    statement_type: Literal["balance-sheet", "income-statement", "cash-flow"]
    title: str = Field(min_length=4)
    language: Literal["en-IN", "hi-IN", "gu-IN"] = "en-IN"
    entity_id: str = Field(pattern=r"^SYN-ENT-[0-9]+$")
    entity_name: str = Field(min_length=2)
    period_start: date
    period_end: date
    currency: Literal["INR"] = "INR"
    line_items: list[FinanceLineItem] = Field(min_length=3, max_length=12)
    total_debits: Decimal
    total_credits: Decimal
    net_position: Decimal
    synthetic: bool = True
    disclaimer: str = "Synthetic financial statement. Not an audited report and not for investment decisions."

    @model_validator(mode="after")
    def validate_structure(self) -> "FinanceStatement":
        if self.period_end < self.period_start:
            raise ValueError("period_end must be on or after period_start")
        if [item.line_id for item in self.line_items] != list(range(1, len(self.line_items) + 1)):
            raise ValueError("line item IDs must be sequential")
        debit_sum = sum((item.amount for item in self.line_items if item.side == "debit"), Decimal("0"))
        credit_sum = sum((item.amount for item in self.line_items if item.side == "credit"), Decimal("0"))
        if debit_sum != self.total_debits or credit_sum != self.total_credits:
            raise ValueError("posted totals must match line items")
        if (self.total_debits - self.total_credits) != self.net_position:
            raise ValueError("net position must equal debits minus credits")
        return self
