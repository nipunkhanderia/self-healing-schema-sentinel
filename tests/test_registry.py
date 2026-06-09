"""Tests for SchemaRegistry — registration, versioning, inference."""
import pytest
from sentinel.registry import SchemaRegistry


def test_register_json_schema(tmp_registry):
    version = tmp_registry.register("bookings", {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {"id": {"type": "string"}}
    })
    assert version.version == "v1"
    assert version.schema_name == "bookings"
    assert version.source == "json_schema"


def test_register_raw_sample_infers_schema(tmp_registry):
    sample = {"flight": "BA123", "price": 299.99, "booked": True}
    version = tmp_registry.register("inferred", sample)
    assert version.source == "inferred"
    assert "properties" in version.schema_dict


def test_version_increments(tmp_registry):
    schema = {"type": "object", "properties": {"x": {"type": "string"}}}
    v1 = tmp_registry.register("s", schema)
    v2 = tmp_registry.register("s", schema)
    assert v1.version == "v1"
    assert v2.version == "v2"


def test_get_latest_returns_most_recent(tmp_registry):
    schema_a = {"type": "object", "properties": {"a": {"type": "string"}}}
    schema_b = {"type": "object", "properties": {"b": {"type": "integer"}}}
    tmp_registry.register("s", schema_a)
    tmp_registry.register("s", schema_b)
    latest = tmp_registry.get_latest("s")
    assert latest.version == "v2"


def test_get_latest_returns_none_for_unknown(tmp_registry):
    assert tmp_registry.get_latest("does_not_exist") is None


def test_list_schemas(tmp_registry):
    tmp_registry.register("alpha", {"type": "object"})
    tmp_registry.register("beta", {"type": "object"})
    schemas = tmp_registry.list_schemas()
    assert "alpha" in schemas
    assert "beta" in schemas
