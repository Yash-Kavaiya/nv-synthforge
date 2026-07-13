from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from app.domain.retail import ProductReview, RetailProduct

_CATEGORIES = ("electronics", "home", "apparel", "grocery")
_CATALOG = {
    "electronics": [
        ("Aurora Noise-Cancel Headphones", "SoundArc"),
        ("PixelPath USB-C Hub", "CircuitNest"),
        ("Nimbus 65W GaN Charger", "VoltHive"),
    ],
    "home": [
        ("CedarFold Storage Bin", "HomeLoom"),
        ("GlideBrew Pour-Over Set", "KitchenOrbit"),
        ("LumenDesk LED Lamp", "NorthNook"),
    ],
    "apparel": [
        ("TrailFlex Running Tee", "MotionThread"),
        ("UrbanKnit Crew Sweater", "Loom & Line"),
        ("MonsoonShield Windbreaker", "Fieldform"),
    ],
    "grocery": [
        ("Malabar Filter Coffee 500g", "SpiceRoute Foods"),
        ("Cold-Pressed Groundnut Oil 1L", "Harvest Cellar"),
        ("Millet Breakfast Mix 400g", "GrainDay"),
    ],
}
_REVIEW_SNIPPETS = [
    ("Solid everyday pick", "Build quality and value are strong for the listed price band."),
    ("Better than expected", "Packaging was intact and the product matched the catalog description."),
    ("Good but not perfect", "Performance is reliable, though the size runs slightly compact."),
    ("Would repurchase", "Delivery was smooth and the listing details were accurate."),
]
_LOCALIZED = {
    "en-IN": "",
    "hi-IN": "[हिन्दी रिटेल] ",
    "gu-IN": "[ગુજરાતી રિટેલ] ",
}


def _money(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class OfflineRetailGenerator:
    def generate(
        self,
        count: int,
        seed: int,
        language: str = "en-IN",
        category: str = "mixed",
        max_reviews: int = 3,
    ) -> list[RetailProduct]:
        rng = random.Random(seed)
        records: list[RetailProduct] = []
        for index in range(count):
            cat = rng.choice(_CATEGORIES) if category == "mixed" else category
            if cat not in _CATEGORIES:
                cat = "electronics"
            title, brand = rng.choice(_CATALOG[cat])
            list_price = _money(rng.uniform(299, 14999))
            discount = Decimal(str(rng.choice([0, 0.05, 0.1, 0.15, 0.2])))
            sale_price = (list_price * (Decimal("1") - discount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            review_n = max(1, min(max_reviews, 5))
            reviews: list[ProductReview] = []
            for review_id in range(1, review_n + 1):
                review_title, body = rng.choice(_REVIEW_SNIPPETS)
                reviews.append(
                    ProductReview(
                        review_id=review_id,
                        rating=rng.randint(3, 5),
                        title=review_title,
                        body=f"{_LOCALIZED.get(language, '')}{body}",
                        reviewer_id=f"SYN-REV-{(seed + index * 10 + review_id) % 1000000:06d}",
                    )
                )
            average = round(sum(review.rating for review in reviews) / len(reviews), 2)
            records.append(
                RetailProduct(
                    product_id=f"RTL-{seed:06d}-{index + 1:04d}",
                    sku=f"SKU-{cat[:3].upper()}-{seed % 10000:04d}{index + 1:02d}",
                    title=title,
                    language=language,  # type: ignore[arg-type]
                    category=cat,  # type: ignore[arg-type]
                    brand=brand,
                    list_price_inr=list_price,
                    sale_price_inr=sale_price,
                    inventory_units=rng.randint(0, 500),
                    rating_average=average,
                    review_count=len(reviews),
                    listed_on=date(2025, 10, 1) + timedelta(days=rng.randint(0, 250)),
                    reviews=reviews,
                    synthetic=True,
                )
            )
        return records
