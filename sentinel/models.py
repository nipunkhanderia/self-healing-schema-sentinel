"""
Shared Pydantic models for schema-sentinel.
All inter-module data flows through these models.
"""
from __future__ import annotations
from enum import Enum
from typing import Any
from datetime import datetime
from pydantic import BaseModel, Field


class DriftType(str, Enum):
    FIELD_ADDED = "field_added"
    FIELD_REMOVED = "field_removed"
    TYPE_CHANGED = "type_changed"
    REQUIRED_CHANGED = "required_changed"
    NO_DRIFT = "no_drift"


class FieldDrift(BaseModel):
    """Represents a single field-level drift event."""
    drift_type: DriftType
    field_path: str           # e.g. "$.baggage.weight" or "$.flight_number"
    old_value: Any = None     # Previous type/value/presence
    new_value: Any = None     # New type/value/presence
    severity: str = "medium"  # "low", "medium", "high"


class DriftReport(BaseModel):
    """Full drift report produced by the differ."""
    schema_name: str
    baseline_version: str
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    drifts: list[FieldDrift] = []
    has_drift: bool = False
    summary: str = ""

    def compute_summary(self) -> None:
        if not self.drifts:
            self.has_drift = False
            self.summary = "No drift detected."
            return
        self.has_drift = True
        counts = {}
        for d in self.drifts:
            counts[d.drift_type] = counts.get(d.drift_type, 0) + 1
        parts = [f"{v}x {k.value.replace('_', ' ')}" for k, v in counts.items()]
        self.summary = f"Drift detected: {', '.join(parts)}"


class SchemaVersion(BaseModel):
    """A stored, versioned schema snapshot."""
    schema_name: str
    version: str              # e.g. "v1", "v2" — auto-incremented
    schema_dict: dict         # The JSON Schema dict
    created_at: datetime = Field(default_factory=datetime.utcnow)
    source: str = "json_schema"  # "json_schema" or "inferred"


class ValidationResult(BaseModel):
    """Result of validating a payload against a schema."""
    is_valid: bool
    schema_name: str
    schema_version: str
    errors: list[str] = []
    payload_snapshot: dict = {}


class HealResult(BaseModel):
    """Result of LLM-based test healing."""
    success: bool
    schema_name: str
    drift_report: DriftReport
    generated_test_code: str = ""
    output_path: str = ""
    pr_url: str = ""
    error: str = ""
