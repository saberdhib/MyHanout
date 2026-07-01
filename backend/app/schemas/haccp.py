"""Schémas Pydantic du carnet HACCP (hygiène + conformité température)."""

from __future__ import annotations

from pydantic import BaseModel


# --- Plan de nettoyage ---
class HygieneTaskIn(BaseModel):
    name: str
    frequency: str = "daily"  # daily | weekly | monthly
    notes: str | None = None


class HygieneTaskOut(BaseModel):
    id: int
    name: str
    frequency: str
    active: bool
    notes: str | None = None
    due: bool  # à faire (pas d'exécution dans la fenêtre de fréquence)
    last_done_at: str | None = None
    last_done_by: str | None = None


class HygieneRecordOut(BaseModel):
    id: int
    task_id: int
    task_name: str | None = None
    done_at: str
    done_by: str | None = None
    note: str | None = None


# --- Conformité température (dérivée de la chaîne du froid) ---
class EquipmentCompliance(BaseModel):
    equipment_id: int
    equipment_name: str
    min_temp_c: float
    max_temp_c: float
    readings: int
    in_range: int
    compliance_pct: float
    last_temp_c: float | None = None
    last_at: str | None = None
    breaches: list[str] = []  # descriptions des derniers écarts


class HaccpRegister(BaseModel):
    """Registre consolidé, prêt à présenter en cas de contrôle."""

    period_days: int
    generated_at: str
    temperature: list[EquipmentCompliance] = []
    hygiene: list[HygieneRecordOut] = []
    tasks_due: int = 0
    explanation: str
