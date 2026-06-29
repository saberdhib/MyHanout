"""Parsing d'une facture : texte OCR -> structure normalisée (stub heuristique).

Implémentation MVP par expressions régulières simples sur le texte du mock.
À terme : extraction structurée via LLM (function calling) + post-validation.
"""

from __future__ import annotations

import re
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.ingestion.ocr.base import OCRResult


class ParsedInvoiceLine(BaseModel):
    description: str
    quantity: float = 0.0
    unit_price: float = 0.0
    line_total: float = 0.0


class ParsedInvoice(BaseModel):
    number: str | None = None
    supplier_name: str | None = None
    issue_date: date | None = None
    due_date: date | None = None
    total_amount: float | None = None
    currency: str = "EUR"
    lines: list[ParsedInvoiceLine] = Field(default_factory=list)


_DATE_RE = re.compile(r"(\d{2})/(\d{2})/(\d{4})")
_LINE_RE = re.compile(r"^(.+?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s*$")


def _parse_date(value: str) -> date | None:
    m = _DATE_RE.search(value)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(0), "%d/%m/%Y").date()
    except ValueError:
        return None


def parse_invoice(ocr: OCRResult) -> ParsedInvoice:
    """Convertit un OCRResult en facture structurée (heuristique simple)."""
    parsed = ParsedInvoice()
    for raw_line in ocr.text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lower = line.lower()
        if lower.startswith("fournisseur"):
            parsed.supplier_name = line.split(":", 1)[-1].strip()
        elif lower.startswith("numero"):
            parsed.number = line.split(":", 1)[-1].strip()
        elif lower.startswith("date"):
            parsed.issue_date = _parse_date(line)
        elif lower.startswith("echeance"):
            parsed.due_date = _parse_date(line)
        elif lower.startswith("total ttc") or lower.startswith("total:"):
            nums = re.findall(r"\d+(?:\.\d+)?", line)
            if nums:
                parsed.total_amount = float(nums[-1])
        else:
            m = _LINE_RE.match(line)
            if m:
                parsed.lines.append(
                    ParsedInvoiceLine(
                        description=m.group(1).strip(),
                        quantity=float(m.group(2)),
                        unit_price=float(m.group(3)),
                        line_total=float(m.group(4)),
                    )
                )
    return parsed
