"""Tests for SchemaDiffer — drift detection accuracy."""
import pytest
from sentinel.differ import SchemaDiffer
from sentinel.models import DriftType


def test_no_drift_when_schemas_identical(tmp_registry):
    schema = {"type": "object", "properties": {"x": {"type": "string"}}}
    tmp_registry.register("s", schema)
    tmp_registry.register("s", schema)
    differ = SchemaDiffer(registry=tmp_registry)
    report = differ.diff("s")
    assert report.has_drift is False


def test_detects_field_added(tmp_registry):
    from tests.conftest import BASELINE_SCHEMA, DRIFTED_SCHEMA
    tmp_registry.register("s", BASELINE_SCHEMA)
    tmp_registry.register("s", DRIFTED_SCHEMA)
    differ = SchemaDiffer(registry=tmp_registry)
    report = differ.diff("s")
    added = [d for d in report.drifts if d.drift_type == DriftType.FIELD_ADDED]
    field_paths = [d.field_path for d in added]
    assert any("baggage_allowance" in p for p in field_paths)


def test_detects_field_removed(tmp_registry):
    from tests.conftest import BASELINE_SCHEMA, DRIFTED_SCHEMA
    tmp_registry.register("s", BASELINE_SCHEMA)
    tmp_registry.register("s", DRIFTED_SCHEMA)
    differ = SchemaDiffer(registry=tmp_registry)
    report = differ.diff("s")
    removed = [d for d in report.drifts if d.drift_type == DriftType.FIELD_REMOVED]
    field_paths = [d.field_path for d in removed]
    assert any("seat_class" in p for p in field_paths)


def test_detects_type_change(tmp_registry):
    from tests.conftest import BASELINE_SCHEMA, DRIFTED_SCHEMA
    tmp_registry.register("s", BASELINE_SCHEMA)
    tmp_registry.register("s", DRIFTED_SCHEMA)
    differ = SchemaDiffer(registry=tmp_registry)
    report = differ.diff("s")
    type_changes = [d for d in report.drifts if d.drift_type == DriftType.TYPE_CHANGED]
    assert any(d.field_path.endswith("price") for d in type_changes)


def test_summary_populated_when_drift_exists(populated_registry):
    differ = SchemaDiffer(registry=populated_registry)
    report = differ.diff("test_schema")
    assert report.has_drift is True
    assert report.summary != ""
    assert "drift" in report.summary.lower()
