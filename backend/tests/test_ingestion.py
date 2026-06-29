"""Tests du pipeline d'ingestion (OCR mock -> parsing -> validation)."""

import pytest

from app.ingestion.etl.pipeline import ingest_invoice_document


@pytest.mark.asyncio
async def test_ingest_mock_invoice():
    result = await ingest_invoice_document(b"", content_type="application/pdf")
    assert result.parsed.supplier_name == "Boucherie Centrale"
    assert result.parsed.number == "FAC-2026-0418"
    assert len(result.parsed.lines) == 2
    assert result.validation.ok is True
