"""
Drift detection engine — compares two JSON Schema versions and classifies changes.

Detects:
  - field_added: new field present in new schema, absent in baseline
  - field_removed: field present in baseline, absent in new schema
  - type_changed: field present in both but type differs
  - required_changed: field moves between required/optional

Usage:
    differ = SchemaDiffer()
    report = differ.diff("flight_booking")  # compares latest two versions
    # or
    report = differ.diff_schemas("flight_booking", schema_v1, schema_v2)
"""
from sentinel.models import DriftReport, FieldDrift, DriftType
from sentinel.registry import SchemaRegistry


class SchemaDiffer:

    def __init__(self, registry: SchemaRegistry | None = None):
        self.registry = registry or SchemaRegistry()

    def diff(self, schema_name: str) -> DriftReport:
        """
        Compare the two most recent versions of a named schema.
        If only one version exists, returns a no-drift report.
        """
        versions = self.registry.get_all_versions(schema_name)
        if len(versions) < 2:
            report = DriftReport(
                schema_name=schema_name,
                baseline_version=versions[0].version if versions else "none",
            )
            report.compute_summary()
            return report

        baseline = versions[-2]
        current = versions[-1]
        return self.diff_schemas(
            schema_name=schema_name,
            baseline=baseline.schema_dict,
            current=current.schema_dict,
            baseline_version=baseline.version,
        )

    def diff_schemas(
        self,
        schema_name: str,
        baseline: dict,
        current: dict,
        baseline_version: str = "baseline",
    ) -> DriftReport:
        """
        Compare two JSON Schema dicts directly.
        Walks the 'properties' tree recursively to find field-level changes.
        """
        drifts: list[FieldDrift] = []
        self._compare_properties(
            baseline_props=baseline.get("properties", {}),
            current_props=current.get("properties", {}),
            baseline_required=set(baseline.get("required", [])),
            current_required=set(current.get("required", [])),
            path="$",
            drifts=drifts,
        )

        report = DriftReport(
            schema_name=schema_name,
            baseline_version=baseline_version,
            drifts=drifts,
        )
        report.compute_summary()
        return report

    def _compare_properties(
        self,
        baseline_props: dict,
        current_props: dict,
        baseline_required: set,
        current_required: set,
        path: str,
        drifts: list[FieldDrift],
    ) -> None:
        baseline_keys = set(baseline_props.keys())
        current_keys = set(current_props.keys())

        # Fields removed
        for key in baseline_keys - current_keys:
            drifts.append(FieldDrift(
                drift_type=DriftType.FIELD_REMOVED,
                field_path=f"{path}.{key}",
                old_value=baseline_props[key].get("type", "unknown"),
                new_value=None,
                severity="high",
            ))

        # Fields added
        for key in current_keys - baseline_keys:
            drifts.append(FieldDrift(
                drift_type=DriftType.FIELD_ADDED,
                field_path=f"{path}.{key}",
                old_value=None,
                new_value=current_props[key].get("type", "unknown"),
                severity="medium",
            ))

        # Fields present in both — check for type change and required change
        for key in baseline_keys & current_keys:
            field_path = f"{path}.{key}"
            b_prop = baseline_props[key]
            c_prop = current_props[key]

            b_type = b_prop.get("type")
            c_type = c_prop.get("type")
            if b_type != c_type:
                drifts.append(FieldDrift(
                    drift_type=DriftType.TYPE_CHANGED,
                    field_path=field_path,
                    old_value=b_type,
                    new_value=c_type,
                    severity="high",
                ))

            b_req = key in baseline_required
            c_req = key in current_required
            if b_req != c_req:
                drifts.append(FieldDrift(
                    drift_type=DriftType.REQUIRED_CHANGED,
                    field_path=field_path,
                    old_value="required" if b_req else "optional",
                    new_value="required" if c_req else "optional",
                    severity="medium",
                ))

            # Recurse into nested objects
            if b_prop.get("type") == "object" and c_prop.get("type") == "object":
                self._compare_properties(
                    baseline_props=b_prop.get("properties", {}),
                    current_props=c_prop.get("properties", {}),
                    baseline_required=set(b_prop.get("required", [])),
                    current_required=set(c_prop.get("required", [])),
                    path=field_path,
                    drifts=drifts,
                )
