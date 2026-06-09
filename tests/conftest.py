"""Shared pytest fixtures for schema-sentinel tests."""
import pytest
import json
from pathlib import Path


BASELINE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["flight_number", "price"],
    "properties": {
        "flight_number": {"type": "string"},
        "price": {"type": "string"},
        "seat_class": {"type": "string"},
    }
}

DRIFTED_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["flight_number", "price"],
    "properties": {
        "flight_number": {"type": "string"},
        "price": {"type": "number"},          # type changed: string → number
        "baggage_allowance": {"type": "integer"},  # field added
        # seat_class removed
    }
}

VALID_PAYLOAD = {
    "flight_number": "BA123",
    "price": "249.99",
    "seat_class": "economy",
}


@pytest.fixture
def tmp_registry(tmp_path):
    """A SchemaRegistry backed by a temp directory."""
    from sentinel.registry import SchemaRegistry
    return SchemaRegistry(store_dir=str(tmp_path / "schemas"))


@pytest.fixture
def populated_registry(tmp_registry):
    """Registry pre-loaded with baseline + drifted schema."""
    tmp_registry.register("test_schema", BASELINE_SCHEMA)
    tmp_registry.register("test_schema", DRIFTED_SCHEMA)
    return tmp_registry
