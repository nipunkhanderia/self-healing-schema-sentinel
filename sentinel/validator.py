"""
Payload validator — validates incoming JSON against the registered baseline schema.

Usage:
    validator = SchemaValidator()
    result = validator.validate("flight_booking", payload_dict)
    if not result.is_valid:
        print(result.errors)
"""
import jsonschema
from sentinel.models import ValidationResult
from sentinel.registry import SchemaRegistry


class SchemaValidator:

    def __init__(self, registry: SchemaRegistry | None = None):
        self.registry = registry or SchemaRegistry()

    def validate(self, schema_name: str, payload: dict) -> ValidationResult:
        """
        Validate payload against the latest registered schema for schema_name.
        Returns ValidationResult with is_valid flag and list of error messages.
        """
        latest = self.registry.get_latest(schema_name)
        if not latest:
            return ValidationResult(
                is_valid=False,
                schema_name=schema_name,
                schema_version="none",
                errors=[f"No schema registered for '{schema_name}'"],
                payload_snapshot=payload,
            )

        errors = []
        validator = jsonschema.Draft7Validator(latest.schema_dict)
        for error in validator.iter_errors(payload):
            errors.append(f"{'.'.join(str(p) for p in error.absolute_path) or 'root'}: {error.message}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            schema_name=schema_name,
            schema_version=latest.version,
            errors=errors,
            payload_snapshot=payload,
        )
