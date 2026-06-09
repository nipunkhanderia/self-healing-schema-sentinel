"""
Tests for TestHealer — mocked so no real LLM calls are made in CI.
Tests the prompt building and output handling logic.
"""
import pytest
from unittest.mock import patch, MagicMock
from sentinel.healer import TestHealer, _build_prompt
from sentinel.models import DriftReport, FieldDrift, DriftType


@pytest.fixture
def sample_drift_report():
    report = DriftReport(
        schema_name="flight_booking",
        baseline_version="v1",
        drifts=[
            FieldDrift(
                drift_type=DriftType.FIELD_ADDED,
                field_path="$.baggage_allowance",
                old_value=None,
                new_value="integer",
                severity="medium",
            ),
            FieldDrift(
                drift_type=DriftType.FIELD_REMOVED,
                field_path="$.seat_class",
                old_value="string",
                new_value=None,
                severity="high",
            ),
        ],
    )
    report.compute_summary()
    return report


def test_build_prompt_contains_schema_name(sample_drift_report):
    prompt = _build_prompt(sample_drift_report, "# existing tests", {})
    assert "flight_booking" in prompt


def test_build_prompt_contains_drift_fields(sample_drift_report):
    prompt = _build_prompt(sample_drift_report, "", {})
    assert "baggage_allowance" in prompt
    assert "seat_class" in prompt


def test_healer_calls_groq_backend(sample_drift_report):
    with patch("sentinel.healer.settings") as mock_settings:
        mock_settings.llm_backend = "groq"
        mock_settings.groq_api_key = "test-key"
        mock_settings.groq_model = "llama-3.3-70b-versatile"

        mock_response = MagicMock()
        mock_response.choices[0].message.content = "def test_baggage_allowance(): assert True"

        with patch("sentinel.healer.Groq") as MockGroq:
            MockGroq.return_value.chat.completions.create.return_value = mock_response
            healer = TestHealer()
            result = healer.generate_tests(sample_drift_report, "", {})
            assert "test_baggage_allowance" in result


def test_healer_raises_for_unknown_backend(sample_drift_report):
    with patch("sentinel.healer.settings") as mock_settings:
        mock_settings.llm_backend = "unknown_llm"
        healer = TestHealer()
        with pytest.raises(RuntimeError, match="Unknown LLM backend"):
            healer.generate_tests(sample_drift_report, "", {})
