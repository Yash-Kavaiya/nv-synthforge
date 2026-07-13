from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from jinja2 import BaseLoader, Environment, select_autoescape
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from pydantic import BaseModel, Field

from app.domain.invoice import Invoice


@dataclass(frozen=True)
class Artifact:
    kind: str
    path: Path


class DegradationConfig(BaseModel):
    blur_radius: float = Field(default=0.8, ge=0, le=10)
    noise_sigma: float = Field(default=6.0, ge=0, le=100)
    jpeg_quality: int = Field(default=72, ge=10, le=100)
    rotation_degrees: float = Field(default=0.4, ge=-10, le=10)
    perspective: float = Field(default=0.0, ge=0, le=0.2)
    stamp_opacity: float = Field(default=0.0, ge=0, le=1)
    contrast: float = Field(default=0.96, ge=0.25, le=2)


_HTML_TEMPLATE = """<!doctype html>
<html lang="{{ language }}"><head><meta charset="utf-8"><title>{{ invoice.invoice_number }}</title>
<style>
@page { size: A4; margin: 18mm; } body { font-family: Arial, sans-serif; color:#172033; font-size:12px; }
h1 { margin:0; font-size:25px; } .top { display:flex; justify-content:space-between; border-bottom:3px solid #76b900; padding-bottom:12px; }
.parties { display:grid; grid-template-columns:1fr 1fr; gap:18px; margin:18px 0; }.box { border:1px solid #ccd2dc; padding:12px; }
table { width:100%; border-collapse:collapse; } th { background:#172033;color:white; } th,td { padding:8px;border:1px solid #ccd2dc;text-align:right; } th:first-child,td:first-child{text-align:left}.totals{margin:16px 0 0 auto;width:45%}.total{font-weight:bold;background:#eef7df}
</style></head><body>
<div class="top"><div><h1>Tax Invoice</h1><b>NV-SynthForge Synthetic Document</b></div><div><b>{{ invoice.invoice_number }}</b><br>{{ invoice.invoice_date }}</div></div>
<div class="parties"><div class="box"><b>Seller</b><br>{{ invoice.seller.name }}<br>{{ invoice.seller.address.line1 }}, {{ invoice.seller.address.city }}<br>{{ invoice.seller.address.state }} {{ invoice.seller.address.postal_code }}<br>GSTIN: {{ invoice.seller.gstin }}</div>
<div class="box"><b>Buyer</b><br>{{ invoice.buyer.name }}<br>{{ invoice.buyer.address.line1 }}, {{ invoice.buyer.address.city }}<br>{{ invoice.buyer.address.state }} {{ invoice.buyer.address.postal_code }}<br>GSTIN: {{ invoice.buyer.gstin }}</div></div>
<table><thead><tr><th>Description</th><th>HSN/SAC</th><th>Qty</th><th>Rate</th><th>GST</th><th>Total</th></tr></thead><tbody>
{% for item in invoice.items %}<tr><td>{{ item.description }}</td><td>{{ item.hsn_sac }}</td><td>{{ item.quantity }}</td><td>₹{{ item.unit_price }}</td><td>{{ item.gst_rate }}%</td><td>₹{{ item.line_total }}</td></tr>{% endfor %}
</tbody></table><table class="totals"><tr><td>Subtotal</td><td>₹{{ invoice.subtotal }}</td></tr><tr><td>CGST</td><td>₹{{ invoice.cgst }}</td></tr><tr><td>SGST</td><td>₹{{ invoice.sgst }}</td></tr><tr><td>IGST</td><td>₹{{ invoice.igst }}</td></tr><tr class="total"><td>Grand total</td><td>₹{{ invoice.grand_total }}</td></tr></table>
<p>Place of supply: {{ invoice.place_of_supply }} · Currency: {{ invoice.currency }}</p><p>{{ invoice.notes or '' }}</p></body></html>"""


class InvoiceRenderer:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.template = Environment(
            loader=BaseLoader(), autoescape=select_autoescape(["html", "xml"])
        ).from_string(_HTML_TEMPLATE)

    def render(self, invoice: Invoice, index: int, language: str = "en-IN") -> list[Artifact]:
        stem = f"invoice-{index:04d}"
        html_path = self.output_dir / f"{stem}.html"
        pdf_path = self.output_dir / f"{stem}.pdf"
        png_path = self.output_dir / f"{stem}.png"
        html = self.template.render(invoice=invoice, language=language)
        html_path.write_text(html, encoding="utf-8")
        self._write_pdf(html, invoice, pdf_path)
        self._write_png(invoice, png_path)
        return [Artifact("html", html_path), Artifact("pdf", pdf_path), Artifact("png", png_path)]

    @staticmethod
    def _write_pdf(html: str, invoice: Invoice, destination: Path) -> None:
        import sys

        if sys.platform != "win32":
            try:
                from weasyprint import HTML

                HTML(string=html).write_pdf(destination)
                return
            except (ImportError, OSError):
                pass
        InvoiceRenderer._write_reportlab_pdf(invoice, destination)

    @staticmethod
    def _write_reportlab_pdf(invoice: Invoice, destination: Path) -> None:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen.canvas import Canvas

        canvas = Canvas(str(destination), pagesize=A4)
        width, height = A4
        canvas.setFont("Helvetica-Bold", 22)
        canvas.drawString(48, height - 58, "TAX INVOICE")
        canvas.setFont("Helvetica", 10)
        canvas.drawRightString(width - 48, height - 52, str(invoice.invoice_date))
        canvas.drawString(48, height - 78, invoice.invoice_number)
        canvas.setStrokeColorRGB(0.46, 0.73, 0)
        canvas.setLineWidth(3)
        canvas.line(48, height - 92, width - 48, height - 92)
        y = height - 122
        for label, party in (("SELLER", invoice.seller), ("BUYER", invoice.buyer)):
            canvas.setFont("Helvetica-Bold", 11)
            canvas.drawString(48, y, label)
            canvas.setFont("Helvetica", 9)
            y -= 16
            for line in (party.name, party.address.line1, f"{party.address.city}, {party.address.state} {party.address.postal_code}", f"GSTIN: {party.gstin}"):
                canvas.drawString(58, y, line)
                y -= 14
            y -= 10
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(48, y, "DESCRIPTION")
        canvas.drawString(300, y, "HSN/SAC")
        canvas.drawRightString(width - 48, y, "TOTAL (INR)")
        y -= 18
        canvas.setFont("Helvetica", 9)
        for item in invoice.items:
            canvas.drawString(48, y, item.description)
            canvas.drawString(300, y, item.hsn_sac)
            canvas.drawRightString(width - 48, y, str(item.line_total))
            y -= 18
        y -= 14
        for label, value in (("Subtotal", invoice.subtotal), ("CGST", invoice.cgst), ("SGST", invoice.sgst), ("IGST", invoice.igst), ("Grand total", invoice.grand_total)):
            canvas.drawRightString(width - 130, y, label)
            canvas.drawRightString(width - 48, y, str(value))
            y -= 17
        canvas.setFont("Helvetica", 8)
        canvas.drawString(48, 42, "Synthetic document - NV-SynthForge")
        canvas.save()

    @staticmethod
    def _write_png(invoice: Invoice, destination: Path) -> None:
        image = Image.new("RGB", (1240, 1754), "white")
        draw = ImageDraw.Draw(image)
        regular = ImageFont.load_default(size=24)
        small = ImageFont.load_default(size=19)
        bold = ImageFont.load_default(size=34)
        green = "#76b900"
        navy = "#172033"
        draw.rectangle((0, 0, 1240, 20), fill=green)
        draw.text((70, 60), "TAX INVOICE", fill=navy, font=bold)
        draw.text((70, 112), invoice.invoice_number, fill=navy, font=regular)
        draw.text((900, 70), str(invoice.invoice_date), fill=navy, font=regular)
        draw.line((70, 160, 1170, 160), fill=green, width=5)
        InvoiceRenderer._draw_party(draw, (70, 205), "SELLER", invoice.seller, regular, small)
        InvoiceRenderer._draw_party(draw, (650, 205), "BUYER", invoice.buyer, regular, small)
        y = 455
        draw.rectangle((70, y, 1170, y + 48), fill=navy)
        headers = [(80, "Description"), (610, "HSN/SAC"), (780, "Qty"), (890, "GST"), (1020, "Total")]
        for x, label in headers:
            draw.text((x, y + 12), label, fill="white", font=small)
        y += 48
        for item in invoice.items:
            draw.rectangle((70, y, 1170, y + 58), outline="#ccd2dc", width=1)
            values = [
                (80, item.description[:38]),
                (610, item.hsn_sac),
                (780, str(item.quantity)),
                (890, f"{item.gst_rate}%"),
                (1020, f"Rs {item.line_total}"),
            ]
            for x, value in values:
                draw.text((x, y + 17), value, fill=navy, font=small)
            y += 58
        y += 55
        totals = [
            ("Subtotal", invoice.subtotal),
            ("CGST", invoice.cgst),
            ("SGST", invoice.sgst),
            ("IGST", invoice.igst),
            ("Grand total", invoice.grand_total),
        ]
        for label, value in totals:
            draw.text((770, y), label, fill=navy, font=regular)
            draw.text((1010, y), f"Rs {value}", fill=navy, font=regular)
            y += 44
        draw.text((70, 1615), "Synthetic document · NV-SynthForge", fill="#687385", font=small)
        image.save(destination, format="PNG", optimize=False)

    @staticmethod
    def _draw_party(draw, origin, title, party, regular, small) -> None:
        x, y = origin
        draw.text((x, y), title, fill="#76b900", font=regular)
        lines = [
            party.name,
            party.address.line1,
            f"{party.address.city}, {party.address.state} {party.address.postal_code}",
            f"GSTIN: {party.gstin}",
        ]
        for offset, line in enumerate(lines, start=1):
            draw.text((x, y + offset * 37), line[:44], fill="#172033", font=small)

    def degrade(self, source: Path, config: DegradationConfig, seed: int, suffix: str = "degraded") -> Path:
        with Image.open(source) as opened:
            image = opened.convert("RGB")
        rng = np.random.default_rng(seed)
        if config.perspective:
            width, height = image.size
            margin = config.perspective * min(width, height)
            jitter = rng.uniform(0.65, 1.0, size=4) * margin
            quadrilateral = (
                float(jitter[0]), float(jitter[0]),
                float(jitter[1]), float(height - jitter[1]),
                float(width - jitter[2]), float(height - jitter[2]),
                float(width - jitter[3]), float(jitter[3]),
            )
            image = image.transform(
                image.size,
                Image.Transform.QUAD,
                quadrilateral,
                resample=Image.Resampling.BICUBIC,
                fillcolor="white",
            )
        if config.rotation_degrees:
            image = image.rotate(config.rotation_degrees, resample=Image.Resampling.BICUBIC, fillcolor="white")
        if config.blur_radius:
            image = image.filter(ImageFilter.GaussianBlur(config.blur_radius))
        if config.contrast != 1:
            image = ImageEnhance.Contrast(image).enhance(config.contrast)
        if config.stamp_opacity:
            overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
            stamp = Image.new("RGBA", (430, 130), (0, 0, 0, 0))
            stamp_draw = ImageDraw.Draw(stamp)
            alpha = round(190 * config.stamp_opacity)
            stamp_draw.rounded_rectangle((8, 8, 422, 122), radius=12, outline=(168, 28, 28, alpha), width=9)
            stamp_draw.text((82, 42), "SYNTHETIC COPY", fill=(168, 28, 28, alpha), font=ImageFont.load_default(size=34))
            stamp = stamp.rotate(-12, resample=Image.Resampling.BICUBIC, expand=True)
            overlay.alpha_composite(stamp, (image.width // 2 - stamp.width // 2, image.height // 2 - stamp.height // 2))
            image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
        if config.noise_sigma:
            values = np.asarray(image, dtype=np.float32)
            noise = rng.normal(0, config.noise_sigma, values.shape)
            image = Image.fromarray(np.clip(values + noise, 0, 255).astype(np.uint8), "RGB")
        destination = source.with_name(f"{source.stem}-{suffix}.jpg")
        image.save(destination, format="JPEG", quality=config.jpeg_quality, optimize=True)
        return destination


class StructuredArtifactExporter:
    """Domain-neutral JSON/JSONL exporter for validated Pydantic records."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, records: list[dict], stem: str) -> list[Artifact]:
        json_path = self.output_dir / f"{stem}.json"
        jsonl_path = self.output_dir / f"{stem}.jsonl"
        json_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        jsonl_path.write_text(
            "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
            encoding="utf-8",
        )
        return [Artifact("json", json_path), Artifact("jsonl", jsonl_path)]


class ArtifactExporter:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, invoices: list[Invoice]) -> list[Artifact]:
        records = [invoice.model_dump(mode="json") for invoice in invoices]
        artifacts = [
            Artifact("json", self._write_json(records)),
            Artifact("jsonl", self._write_jsonl(records)),
            Artifact("csv", self._write_csv(records)),
        ]
        parquet = self._write_parquet(records)
        if parquet is not None:
            artifacts.append(Artifact("parquet", parquet))
        artifacts.append(Artifact("dataset-card", self._write_dataset_card(len(records))))
        return artifacts

    def _write_json(self, records: list[dict]) -> Path:
        path = self.output_dir / "invoices.json"
        path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def _write_jsonl(self, records: list[dict]) -> Path:
        path = self.output_dir / "invoices.jsonl"
        path.write_text("\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n", encoding="utf-8")
        return path

    def _write_csv(self, records: list[dict]) -> Path:
        path = self.output_dir / "invoices.csv"
        rows = [self._flatten(record) for record in records]
        fieldnames = list(rows[0]) if rows else ["invoice_number"]
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def _write_parquet(self, records: list[dict]) -> Path | None:
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError:
            return None
        path = self.output_dir / "invoices.parquet"
        rows = [self._flatten(record) for record in records]
        pq.write_table(pa.Table.from_pylist(rows), path)
        return path

    def _write_dataset_card(self, count: int) -> Path:
        path = self.output_dir / "README.md"
        path.write_text(
            "---\nlicense: cc-by-4.0\ntask_categories:\n- tabular-classification\n"
            "language:\n- en\n- hi\n- gu\n---\n# NV-SynthForge Invoices\n\n"
            f"Hugging Face-compatible synthetic invoice dataset with {count} records.\n",
            encoding="utf-8",
        )
        return path

    @staticmethod
    def _flatten(record: dict) -> dict:
        return {
            "invoice_number": record["invoice_number"],
            "invoice_date": record["invoice_date"],
            "currency": record["currency"],
            "seller_name": record["seller"]["name"],
            "seller_gstin": record["seller"]["gstin"],
            "buyer_name": record["buyer"]["name"],
            "buyer_gstin": record["buyer"]["gstin"],
            "subtotal": record["subtotal"],
            "cgst": record["cgst"],
            "sgst": record["sgst"],
            "igst": record["igst"],
            "grand_total": record["grand_total"],
            "items_json": json.dumps(record["items"], ensure_ascii=False),
        }
