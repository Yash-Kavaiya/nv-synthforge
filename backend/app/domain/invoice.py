from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from pydantic import BaseModel, Field, field_validator, model_validator

MONEY = Decimal("0.01")
GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")


def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


class Address(BaseModel):
    line1: str = Field(min_length=1)
    line2: str | None = None
    city: str = Field(min_length=1)
    state: str = Field(min_length=1)
    state_code: str = Field(pattern=r"^[0-9]{2}$")
    postal_code: str = Field(pattern=r"^[1-9][0-9]{5}$")


class Party(BaseModel):
    name: str = Field(min_length=2)
    gstin: str
    address: Address

    @field_validator("gstin")
    @classmethod
    def valid_gstin(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not GSTIN_RE.fullmatch(normalized):
            raise ValueError("gstin must match the 15-character Indian GSTIN format")
        return normalized


class InvoiceItem(BaseModel):
    description: str = Field(min_length=1)
    hsn_sac: str = Field(pattern=r"^[0-9]{4,8}$")
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    gst_rate: Decimal = Field(ge=0, le=100)
    line_subtotal: Decimal = Decimal("0.00")
    tax_amount: Decimal = Decimal("0.00")
    line_total: Decimal = Decimal("0.00")

    @model_validator(mode="after")
    def calculate(self) -> InvoiceItem:
        self.line_subtotal = money(self.quantity * self.unit_price)
        self.tax_amount = money(self.line_subtotal * self.gst_rate / Decimal("100"))
        self.line_total = money(self.line_subtotal + self.tax_amount)
        return self


class Invoice(BaseModel):
    invoice_number: str = Field(min_length=1, max_length=64)
    invoice_date: date
    seller: Party
    buyer: Party
    items: list[InvoiceItem] = Field(min_length=1, max_length=100)
    currency: str = Field(default="INR", pattern=r"^[A-Z]{3}$")
    place_of_supply: str | None = None
    notes: str | None = None
    subtotal: Decimal = Decimal("0.00")
    cgst: Decimal = Decimal("0.00")
    sgst: Decimal = Decimal("0.00")
    igst: Decimal = Decimal("0.00")
    grand_total: Decimal = Decimal("0.00")

    @model_validator(mode="after")
    def calculate(self) -> Invoice:
        self.subtotal = money(sum((item.line_subtotal for item in self.items), Decimal("0")))
        total_tax = money(sum((item.tax_amount for item in self.items), Decimal("0")))
        if self.seller.address.state_code == self.buyer.address.state_code:
            self.cgst = money(total_tax / Decimal("2"))
            self.sgst = money(total_tax - self.cgst)
            self.igst = Decimal("0.00")
        else:
            self.cgst = Decimal("0.00")
            self.sgst = Decimal("0.00")
            self.igst = total_tax
        self.grand_total = money(self.subtotal + total_tax)
        self.place_of_supply = self.place_of_supply or self.buyer.address.state
        return self
