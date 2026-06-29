"""Validation métier des factures parsées (avant persistance)."""

from __future__ import annotations

from pydantic import BaseModel

from app.ingestion.parsing.invoice_parser import ParsedInvoice


class ValidationIssue(BaseModel):
    field: str
    level: str  # "error" | "warning"
    message: str


class ValidationReport(BaseModel):
    ok: bool
    issues: list[ValidationIssue] = []


def validate_invoice(invoice: ParsedInvoice) -> ValidationReport:
    """Contrôles de cohérence simples ; renvoie un rapport bloquant/non-bloquant."""
    issues: list[ValidationIssue] = []

    if not invoice.number:
        issues.append(ValidationIssue(field="number", level="warning", message="Numéro absent"))
    if not invoice.supplier_name:
        issues.append(
            ValidationIssue(field="supplier_name", level="error", message="Fournisseur absent")
        )
    if not invoice.lines:
        issues.append(ValidationIssue(field="lines", level="error", message="Aucune ligne"))

    # Cohérence du total (somme des lignes vs total annoncé, tolérance 1%).
    lines_total = sum(line.line_total for line in invoice.lines)
    if invoice.total_amount and lines_total:
        delta = abs(lines_total - invoice.total_amount) / invoice.total_amount
        if delta > 0.01:
            issues.append(
                ValidationIssue(
                    field="total_amount",
                    level="warning",
                    message=f"Total incohérent (lignes={lines_total:.2f}, "
                    f"déclaré={invoice.total_amount:.2f})",
                )
            )

    has_error = any(i.level == "error" for i in issues)
    return ValidationReport(ok=not has_error, issues=issues)
