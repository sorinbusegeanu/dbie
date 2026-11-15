from datetime import UTC, datetime

import pytest

from dbie.domain.commercial import (
    CommercialAssumptions,
    CommercialInput,
    CommercialEvidenceGrade,
    ValueBasis,
    calculate_economics,
    grade_commercial_evidence,
)
from dbie.domain.decisions import ReadinessPolicy, assess_decision_readiness
from dbie.domain.enums import (
    AssumptionCategory,
    AssumptionCriticality,
    CommercialEvidenceClass,
    DecisionType,
    EvidenceDirection,
    EvidenceScope,
    EvidenceTier,
    EvidenceType,
)
from dbie.domain.models import (
    Assumption,
    AutonomousScalability,
    BusinessIdea,
    DigitalEligibility,
    EvidenceItem,
)


def input_value(value, *, basis=ValueBasis.ASSUMPTION, reason=None):
    if value is None:
        basis = ValueBasis.UNKNOWN
    return CommercialInput(value=value, basis=basis, reason_unknown=reason)


def assumptions(**overrides):
    values = {
        "currency": "USD",
        "period_months": 12,
        "customers_at_start": input_value(0),
        "new_customers_per_month": input_value(100),
        "monthly_price": input_value(100),
        "monthly_conversion_rate": input_value(0.1),
        "monthly_retention_rate": input_value(0.9),
        "contribution_margin": input_value(0.8),
        "gross_margin": input_value(0.8),
        "fixed_cost_per_month": input_value(1000),
        "variable_cost_per_customer": input_value(20),
        "acquisition_spend_per_month": input_value(2000),
        "initial_investment": input_value(10000),
        "months_to_first_revenue": input_value(2),
        "customer_lifetime_months": input_value(12),
    }
    values.update(overrides)
    return CommercialAssumptions(**values)


def make_evidence(identifier, lineage, *, grade, scope=EvidenceScope.PRODUCT, direction=EvidenceDirection.SUPPORTS):
    return EvidenceItem(
        run_id="run",
        source_identifier=identifier,
        source_type="interview",
        extracted_fact="A recorded synthetic commercial observation.",
        tier=EvidenceTier.PRIMARY,
        evidence_type=EvidenceType.OBSERVED,
        direction=direction,
        reliability_score=0.9,
        freshness_score=1,
        lineage_group_id=lineage,
        content_hash=(identifier * 32)[:32],
        supported_assumption_ids=["a"],
        commercial_classification=grade,
        commercial_scope=scope,
    )


def idea(*, eligible=True):
    return BusinessIdea(
        run_id="run",
        problem_id="problem",
        title="Digital workflow",
        one_sentence_thesis="Automate a recurring workflow.",
        target_customer="Small firms",
        buyer="Operations lead",
        value_proposition="Save time",
        product_form="SaaS",
        delivery_model="Self-service",
        digital_eligibility=DigitalEligibility(**{name: eligible for name in DigitalEligibility.model_fields}),
        autonomous_scalability=AutonomousScalability(
            target_automation_ratio=0.9,
            human_minutes_per_customer=10,
            human_minutes_per_customer_at_10x=1,
            credible_transition_plan=True,
        ),
    )


def test_economics_calculates_scenarios_and_marks_unknowns():
    result = calculate_economics(assumptions())
    base = result.scenarios["base"]
    assert base.cac == pytest.approx(200)
    assert base.ltv == pytest.approx(960)
    assert base.break_even_customers == pytest.approx(12.5)
    assert base.revenue > 0
    assert result.scenarios["optimistic"].revenue > base.revenue
    assert base.payback_months is not None

    unknown = calculate_economics(assumptions(monthly_price=input_value(None, reason="No price evidence")))
    assert unknown.scenarios["base"].ltv is None
    assert unknown.scenarios["base"].unknowns["ltv"]
    assert unknown.scenarios["base"].revenue is None
    assert unknown.scenarios["base"].unknowns["revenue"] == "Monthly price is unknown."

    derived_margin = calculate_economics(
        assumptions(
            gross_margin=input_value(None, reason="Not separately recorded."),
            contribution_margin=input_value(None, reason="Not separately recorded."),
        )
    ).scenarios["base"]
    assert derived_margin.contribution_margin == pytest.approx(0.8)
    assert derived_margin.gross_margin == pytest.approx(0.8)


def test_scenarios_preserve_observed_values_without_recorded_ranges():
    result = calculate_economics(
        assumptions(
            monthly_price=CommercialInput(value=100, basis=ValueBasis.OBSERVED, evidence_ids=["price-evidence"]),
        )
    )
    assert result.scenarios["pessimistic"].scenario_adjustments["monthly_price"] == "observed_value_fixed_no_recorded_range"
    assert result.scenarios["pessimistic"].scenario_adjustments["monthly_price"] == result.scenarios["optimistic"].scenario_adjustments["monthly_price"]


def test_zero_acquisition_and_negative_unit_economics_are_unknown():
    result = calculate_economics(
        assumptions(new_customers_per_month=input_value(0), monthly_price=input_value(10), variable_cost_per_customer=input_value(20))
    ).scenarios["base"]
    assert result.cac is None
    assert result.break_even_customers is None
    assert "break_even_customers" in result.unknowns


def test_commercial_input_rejects_unverifiable_observed_values_and_bad_ranges():
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="evidence references"):
        CommercialInput(value=10, basis=ValueBasis.OBSERVED)
    with pytest.raises(ValidationError, match="lower bound"):
        CommercialInput(value=10, basis=ValueBasis.ASSUMPTION, lower=12, upper=8)


def test_commercial_evidence_deduplicates_lineages_and_keeps_conflict():
    items = [
        make_evidence("same-a", "shared", grade=CommercialEvidenceClass.PURCHASE_INTENT),
        make_evidence("same-b", "shared", grade=CommercialEvidenceClass.OBSERVED_TRANSACTION),
        make_evidence("against", "other", grade=CommercialEvidenceClass.CUSTOMER_VALIDATION, direction=EvidenceDirection.CONTRADICTS),
    ]
    grade = grade_commercial_evidence(["a"], items)[0]
    assert grade.independent_sources == 2
    assert grade.supporting_grade is CommercialEvidenceClass.OBSERVED_TRANSACTION
    assert grade.contradicting_grade is CommercialEvidenceClass.CUSTOMER_VALIDATION
    assert grade.product_supporting_grade is CommercialEvidenceClass.OBSERVED_TRANSACTION


def test_commercial_evidence_deduplicates_same_source_id_and_ignores_model_judgment():
    first = make_evidence("same-source", "lineage-1", grade=CommercialEvidenceClass.CUSTOMER_VALIDATION)
    duplicate = make_evidence("same-source", "lineage-2", grade=CommercialEvidenceClass.PURCHASE_INTENT).model_copy(update={"source_identifier": "same-source"})
    model = make_evidence("model", "model-lineage", grade=CommercialEvidenceClass.OBSERVED_TRANSACTION).model_copy(update={"tier": EvidenceTier.MODEL_ONLY, "evidence_type": EvidenceType.MODEL_JUDGMENT})
    grade = grade_commercial_evidence(["a"], [first, duplicate, model])[0]
    assert grade.independent_sources == 1
    assert grade.supporting_grade is CommercialEvidenceClass.PURCHASE_INTENT
    assert grade.coverage == 1


def test_hard_eligibility_failure_cannot_be_overridden_by_evidence():
    assessment = assess_decision_readiness(idea(eligible=False), [], [], calculate_economics(assumptions()))
    assert assessment.recommendation is DecisionType.KILL
    assert "HARD_ELIGIBILITY_FAILURE" in assessment.reason_codes
    assert assessment.readiness_score == 0


def test_readiness_requires_customer_validation_and_positive_economics():
    candidate = idea()
    assumption = Assumption(
        run_id="run", idea_id=candidate.id, category=AssumptionCategory.WTP,
        statement="The buyer will pay for the product.", criticality=AssumptionCriticality.FATAL,
        falsification_condition="No buyer chooses a paid plan.",
        validation_condition="Independent buyers choose a paid plan.",
        status="RESEARCH_SUPPORTED",
    )
    evidence = [
        make_evidence(f"source-{i}", f"lineage-{i}", grade=CommercialEvidenceClass.PURCHASE_INTENT)
        for i in range(2)
    ]
    for item in evidence:
        item.supported_assumption_ids = [assumption.id]
    grades = grade_commercial_evidence([assumption.id], evidence)
    policy = {
        "minimum_evidence_coverage": 0,
        "minimum_independent_sources": 2,
        "minimum_ltv_to_cac": 3,
        "maximum_scenario_spread": 3,
    }
    result = assess_decision_readiness(
        candidate, [assumption], grades, calculate_economics(assumptions()),
        policy=ReadinessPolicy(**policy),
        implementation_feasible=True, differentiation_supported=True,
    )
    assert result.recommendation is DecisionType.BUILD
    assert result.supporting_evidence_ids == sorted(item.id for item in evidence)
    assert result.readiness_score > 0
    uncertain = assess_decision_readiness(
        candidate, [assumption], grades, calculate_economics(assumptions()),
        policy=ReadinessPolicy(**(policy | {"maximum_scenario_spread": 0})),
        implementation_feasible=True, differentiation_supported=True,
    )
    assert uncertain.recommendation is DecisionType.MORE_EVIDENCE
    assert "SCENARIO_UNCERTAINTY_ABOVE_THRESHOLD" in uncertain.reason_codes

