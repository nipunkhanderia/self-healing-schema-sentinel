"""Tests for SchemaValidator."""
import pytest
from sentinel.validator import SchemaValidator


def test_valid_payload_passes(populated_registry):
    # populated_registry has v1 (baseline) and v2 (drifted) — latest is v2
    # Use a standalone registry with only v1 for this test
    from sentinel.registry import SchemaRegistry
    from tests.conftest import BASELINE_SCHEMA, VALID_PAYLOAD

    registry = populated_registry.__class__.__new__(populated_registry.__class__)
    # Re-register only baseline
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmpdir:
        r = SchemaRegistry(store_dir=tmpdir)
        r.register("t", BASELINE_SCHEMA)
        validator = SchemaValidator(registry=r)
        result = validator.validate("t", VALID_PAYLOAD)
        assert result.is_valid is True
        assert result.errors == []


def test_invalid_payload_reports_errors(tmp_registry):
    from tests.conftest import BASELINE_SCHEMA
    tmp_registry.register("t", BASELINE_SCHEMA)
    validator = SchemaValidator(registry=tmp_registry)
    bad_payload = {"seat_class": "economy"}  # missing required: flight_number, price
    result = validator.validate("t", bad_payload)
    assert result.is_valid is False
    assert len(result.errors) > 0


def test_unknown_schema_returns_error(tmp_registry):
    validator = SchemaValidator(registry=tmp_registry)
    result = validator.validate("nonexistent", {"x": 1})
    assert result.is_valid is False
    assert "No schema registered" in result.errors[0]
