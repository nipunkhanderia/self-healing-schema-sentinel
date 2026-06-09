"""
Schema registry — stores and retrieves versioned JSON Schema snapshots.

Usage:
    registry = SchemaRegistry()
    version = registry.register("flight_booking", raw_json_sample_dict)
    latest = registry.get_latest("flight_booking")
"""
import json
import os
from pathlib import Path
from genson import SchemaBuilder
from sentinel.models import SchemaVersion
from sentinel.config import settings


class SchemaRegistry:

    def __init__(self, store_dir: str | None = None):
        self.store_dir = Path(store_dir or settings.schema_store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)

    def _schema_dir(self, name: str) -> Path:
        d = self.store_dir / name
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _next_version(self, name: str) -> str:
        existing = self.get_all_versions(name)
        return f"v{len(existing) + 1}"

    def infer_schema(self, sample: dict) -> dict:
        """Use genson to infer a JSON Schema from a raw JSON sample."""
        builder = SchemaBuilder()
        builder.add_object(sample)
        return builder.to_schema()

    def register(self, name: str, data: dict, source: str = "json_schema") -> SchemaVersion:
        """
        Register a schema.
        - If data looks like a raw JSON payload (no '$schema' key), infer schema from it.
        - If data is already a JSON Schema (has '$schema' or 'properties'), store directly.
        Returns the new SchemaVersion.
        """
        is_schema = "$schema" in data or "properties" in data or "type" in data
        if not is_schema:
            schema_dict = self.infer_schema(data)
            source = "inferred"
        else:
            schema_dict = data

        version = SchemaVersion(
            schema_name=name,
            version=self._next_version(name),
            schema_dict=schema_dict,
            source=source,
        )
        path = self._schema_dir(name) / f"{version.version}.json"
        path.write_text(version.model_dump_json(indent=2))
        return version

    def get_latest(self, name: str) -> SchemaVersion | None:
        versions = self.get_all_versions(name)
        return versions[-1] if versions else None

    def get_all_versions(self, name: str) -> list[SchemaVersion]:
        d = self._schema_dir(name)
        files = sorted(d.glob("v*.json"), key=lambda p: int(p.stem[1:]))
        result = []
        for f in files:
            result.append(SchemaVersion.model_validate_json(f.read_text()))
        return result

    def list_schemas(self) -> list[str]:
        return [d.name for d in self.store_dir.iterdir() if d.is_dir()]
