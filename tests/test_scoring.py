import pytest

from dbie.domain.enums import EvidenceType
from dbie.domain.scoring import MetricValue, calculate_triage


def test_unknown_dimensions_remain_uncovered() -> None:
    result = calculate_triage(
        {
            "problem_severity": MetricValue(
                lower=6,
                base=7,
                upper=8,
                evidence_type=EvidenceType.OBSERVED,
            )
        }
    )

    assert result.base == 7
    assert result.coverage == pytest.approx(0.12)


def test_no_metrics_returns_full_uncertainty() -> None:
    result = calculate_triage({})

    assert (result.lower, result.base, result.upper, result.coverage) == (0, 0, 10, 0)
