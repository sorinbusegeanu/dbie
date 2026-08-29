from dbie.domain.eligibility import evaluate_eligibility
from dbie.domain.models import AutonomousScalability, DigitalEligibility
from tests.conftest import make_idea


def test_physical_business_is_rejected_regardless_of_other_fields() -> None:
    digital = DigitalEligibility(
        product_service=False,
        acquisition=True,
        sales=True,
        fulfilment=False,
        operations=True,
        infrastructure=False,
        payments=True,
        support=True,
        scaling=False,
        geography=True,
    )
    result = evaluate_eligibility(make_idea(digital_eligibility=digital))

    assert result.eligible is False
    assert "DIGITAL_PRODUCT_SERVICE_FAILED" in result.reason_codes
    assert "DIGITAL_FULFILMENT_FAILED" in result.reason_codes


def test_labor_linear_service_fails_autonomous_scalability() -> None:
    scalability = AutonomousScalability(
        target_automation_ratio=0,
        human_minutes_per_customer=60,
        human_minutes_per_customer_at_10x=60,
        human_only_tasks=["all delivery"],
        credible_transition_plan=False,
    )
    result = evaluate_eligibility(make_idea(autonomous_scalability=scalability))

    assert result.eligible is False
    assert set(result.reason_codes) >= {
        "AUTOMATION_TRANSITION_NOT_CREDIBLE",
        "AUTOMATION_TARGET_MISSING",
        "HUMAN_BURDEN_NOT_IMPROVING_AT_10X",
    }


def test_fully_digital_scalable_idea_passes() -> None:
    result = evaluate_eligibility(make_idea())

    assert result.eligible is True
    assert result.reason_codes == []
