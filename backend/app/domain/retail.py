from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProductReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_id: int = Field(ge=1)
    rating: int = Field(ge=1, le=5)
    title: str = Field(min_length=2)
    body: str = Field(min_length=8)
    reviewer_id: str = Field(pattern=r"^SYN-REV-[0-9]+$")


class RetailProduct(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: str = Field(pattern=r"^RTL-[A-Z0-9-]+$")
    sku: str = Field(pattern=r"^SKU-[A-Z0-9-]+$")
    title: str = Field(min_length=4)
    language: Literal["en-IN", "hi-IN", "gu-IN"] = "en-IN"
    category: Literal["electronics", "home", "apparel", "grocery"]
    brand: str = Field(min_length=2)
    list_price_inr: Decimal = Field(gt=0)
    sale_price_inr: Decimal = Field(gt=0)
    inventory_units: int = Field(ge=0)
    rating_average: float = Field(ge=1, le=5)
    review_count: int = Field(ge=1)
    listed_on: date
    reviews: list[ProductReview] = Field(min_length=1, max_length=5)
    synthetic: bool = True
    disclaimer: str = "Synthetic retail product record. Not a real catalog listing or customer review."

    @model_validator(mode="after")
    def validate_structure(self) -> "RetailProduct":
        if self.sale_price_inr > self.list_price_inr:
            raise ValueError("sale price cannot exceed list price")
        if [review.review_id for review in self.reviews] != list(range(1, len(self.reviews) + 1)):
            raise ValueError("review IDs must be sequential")
        if self.review_count != len(self.reviews):
            raise ValueError("review_count must match reviews length")
        average = sum(review.rating for review in self.reviews) / len(self.reviews)
        if abs(average - self.rating_average) > 0.05:
            raise ValueError("rating_average must match review ratings")
        return self
