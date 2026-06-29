"""Couche financière — intelligence (classification + alertes)."""

from app.intelligence.finance.classifier import (
    ClassificationResult,
    ExpenseClassifier,
    get_expense_classifier,
)

__all__ = ["ClassificationResult", "ExpenseClassifier", "get_expense_classifier"]
