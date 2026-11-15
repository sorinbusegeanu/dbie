"""Deterministic commercial economics and evidence grading."""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from math import prod
from pydantic import BaseModel, ConfigDict, Field, model_validator

from dbie.domain.enums import (
    CommercialEvidenceClass,
    EvidenceDirection,
    EvidenceTier,
    EvidenceType,
)
from dbie.domain.models import EvidenceItem


class ValueBasis(StrEnum):
    OBSERVED = "OBSERVED"
    ASSUMPTION = "ASSUMPTION"
    ESTIMATE = "ESTIMATE"
    UNKNOWN = "UNKNOWN"


class CommercialInput(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    value: float | None = None
    basis: ValueBasis
    evidence_ids: list[str] = Field(default_factory=list)
    lower: float | None = None
    upper: float | None = None
    reason_unknown: str | None = None
    note: str | None = None

    @model_validator(mode="after")
    def value_has_basis_and_uncertainty(self) -> CommercialInput:
        if self.value is None:
            if not self.reason_unknown:
                raise ValueError("unknown commercial values require a reason")
        elif self.basis is ValueBasis.UNKNOWN:
            raise ValueError("a known value cannot have UNKNOWN basis")
        elif self.basis is ValueBasis.OBSERVED and not self.evidence_ids:
            raise ValueError("observed commercial values require evidence references")
        if self.lower is not None and self.upper is not None and self.lower > self.upper:
            raise ValueError("uncertainty lower bound cannot exceed upper bound")
        if self.value is not None and self.lower is not None and self.value < self.lower:
            raise ValueError("value cannot be below its uncertainty range")
        if self.value is not None and self.upper is not None and self.value > self.upper:
            raise ValueError("value cannot exceed its uncertainty range")
        return self


class CommercialAssumptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    currency: str = "USD"
    period_months: int = Field(default=12, gt=0)
    customers_at_start: CommercialInput
    new_customers_per_month: CommercialInput
    monthly_price: CommercialInput
    monthly_conversion_rate: CommercialInput
    monthly_retention_rate: CommercialInput
    contribution_margin: CommercialInput
    gross_margin: CommercialInput
    fixed_cost_per_month: CommercialInput
    variable_cost_per_customer: CommercialInput
    acquisition_spend_per_month: CommercialInput
    initial_investment: CommercialInput
    months_to_first_revenue: CommercialInput
    customer_lifetime_months: CommercialInput

    @model_validator(mode="after")
    def coherent_units_and_ranges(self) -> CommercialAssumptions:
        if len(self.currency) != 3 or not self.currency.isalpha() or self.currency != self.currency.upper():
            raise ValueError("currency must be a three-letter uppercase currency code")
        for name in ("monthly_conversion_rate", "monthly_retention_rate", "gross_margin", "contribution_margin"):
            item = getattr(self, name)
            values = [value for value in (item.value, item.lower, item.upper) if value is not None]
            if name in {"monthly_conversion_rate", "monthly_retention_rate"} and any(not 0 <= value <= 1 for value in values):
                raise ValueError(f"{name} is outside its valid range")
            if name in {"gross_margin", "contribution_margin"} and any(value > 1 for value in values):
                raise ValueError(f"{name} cannot exceed one")
        for name in (
            "customers_at_start", "new_customers_per_month", "monthly_price",
            "fixed_cost_per_month", "variable_cost_per_customer",
            "acquisition_spend_per_month", "initial_investment",
            "months_to_first_revenue", "customer_lifetime_months",
        ):
            item = getattr(self, name)
            values = [value for value in (item.value, item.lower, item.upper) if value is not None]
            if any(value < 0 for value in values):
                raise ValueError(f"{name} cannot be negative")
        if self.customer_lifetime_months.value == 0:
            raise ValueError("customer lifetime must be positive when supplied")
        if self.customer_lifetime_months.lower == 0:
            raise ValueError("customer lifetime lower bound must be positive")
        return self


class ScenarioResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    ending_customers: float | None
    revenue: float | None
    cac: float | None
    ltv: float | None
    gross_margin: float | None
    contribution_margin: float | None
    break_even_customers: float | None
    break_even_revenue: float | None
    initial_investment: float | None
    payback_months: float | None
    first_revenue_month: float | None
    scenario_adjustments: dict[str, str] = Field(default_factory=dict)
    unknowns: dict[str, str] = Field(default_factory=dict)


class CommercialEconomics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    currency: str
    period_months: int
    assumptions: CommercialAssumptions
    scenarios: dict[str, ScenarioResult]


def estimated_business_model_inputs(
    monthly_price: float | None,
    variable_cost_per_customer: float | None,
    *,
    currency: str = "USD",
    monthly_leads: float | None = None,
    conversion_rate: float | None = None,
    monthly_fixed_cost: float | None = None,
    acquisition_spend: float | None = None,
    initial_investment: float | None = None,
    customer_lifetime_months: float | None = None,
) -> CommercialAssumptions:
    """Adapt business-model estimates to the engine, explicitly marking gaps."""
    def item(value: float | None, reason: str, *, note: str | None = None) -> CommercialInput:
        return CommercialInput(
            value=value,
            basis=ValueBasis.ESTIMATE if value is not None else ValueBasis.UNKNOWN,
            reason_unknown=None if value is not None else reason,
            note=note if value is not None else None,
        )

    margin = (
        (monthly_price - variable_cost_per_customer) / monthly_price
        if monthly_price and variable_cost_per_customer is not None
        else None
    )
    return CommercialAssumptions(
        currency=currency,
        period_months=12,
        customers_at_start=item(0, "Starting customer count was not supplied.", note="Scenario starts from zero customers."),
        new_customers_per_month=item(monthly_leads, "Monthly qualified leads were not supplied."),
        monthly_price=item(monthly_price, "Monthly price was not supplied.", note="Business-model narrative estimate; unvalidated until tested with buyers."),
        monthly_conversion_rate=item(conversion_rate, "Conversion rate was not supplied."),
        monthly_retention_rate=item(0.95, "Retention assumption defaulted to an illustrative 95% monthly.", note="Illustrative monthly retention assumption; replace with cohort observations."),
        contribution_margin=item(margin, "Price and variable cost are needed to estimate contribution margin.", note="Calculated from estimated price and variable cost per customer."),
        gross_margin=item(margin, "Price and variable cost are needed to estimate gross margin.", note="Calculated from estimated price and variable cost per customer."),
        fixed_cost_per_month=item(monthly_fixed_cost, "Fixed operating costs were not supplied."),
        variable_cost_per_customer=item(variable_cost_per_customer, "Variable cost per customer was not supplied.", note="Business-model narrative estimate; unvalidated until measured."),
        acquisition_spend_per_month=item(acquisition_spend, "Acquisition spend was not supplied."),
        initial_investment=item(initial_investment, "Initial investment requirement was not supplied."),
        months_to_first_revenue=item(None, "Launch timeline and first revenue date were not supplied."),
        customer_lifetime_months=item(customer_lifetime_months, "Customer lifetime assumption was not supplied."),
    )


def _v(item: CommercialInput, name: str, unknowns: dict[str, str]) -> float | None:
    if item.value is None:
        unknowns[name] = item.reason_unknown or "No value was recorded."
    return item.value


def _scenario(assumptions: CommercialAssumptions, name: str) -> ScenarioResult:
    unknowns: dict[str, str] = {}
    adverse = name == "pessimistic"
    adjustments: dict[str, str] = {}

    def pick(field: str, input_value: CommercialInput, *, cost: bool = False) -> float | None:
        value = _v(input_value, field, unknowns)
        if value is None or name == "base":
            return value
        use_lower = adverse != cost
        bound = input_value.lower if use_lower else input_value.upper
        if bound is not None:
            adjustments[field] = "recorded_lower_bound" if use_lower else "recorded_upper_bound"
            return bound
        if input_value.basis is ValueBasis.OBSERVED:
            adjustments[field] = "observed_value_fixed_no_recorded_range"
            return value
        multiplier = 1.25 if adverse == cost else 0.75
        adjustments[field] = f"estimated_sensitivity_x{multiplier:.2f}"
        return value * multiplier

    start = pick("customers_at_start", assumptions.customers_at_start)
    leads = pick("qualified_leads_per_month", assumptions.new_customers_per_month)
    price = pick("monthly_price", assumptions.monthly_price)
    conversion = pick("monthly_conversion_rate", assumptions.monthly_conversion_rate)
    retention = pick("monthly_retention_rate", assumptions.monthly_retention_rate)
    contribution = pick("contribution_margin", assumptions.contribution_margin)
    gross = pick("gross_margin", assumptions.gross_margin)
    fixed = pick("fixed_cost_per_month", assumptions.fixed_cost_per_month, cost=True)
    variable = pick("variable_cost_per_customer", assumptions.variable_cost_per_customer, cost=True)
    spend = pick("acquisition_spend_per_month", assumptions.acquisition_spend_per_month, cost=True)
    investment = pick("initial_investment", assumptions.initial_investment, cost=True)
    first = pick("months_to_first_revenue", assumptions.months_to_first_revenue, cost=True)
    lifetime = pick("customer_lifetime_months", assumptions.customer_lifetime_months)
    conversion = None if conversion is None else min(1.0, max(0.0, conversion))
    retention = None if retention is None else min(1.0, max(0.0, retention))
    if price is not None and price > 0 and variable is not None:
        derived_margin = (price - variable) / price
        gross = derived_margin
        unknowns.pop("gross_margin", None)
        adjustments["gross_margin"] = "derived_from_price_and_variable_cost"
        if contribution is None:
            contribution = derived_margin
            unknowns.pop("contribution_margin", None)
            adjustments["contribution_margin"] = "derived_from_price_and_variable_cost"
        contribution_equals_gross = (
            assumptions.contribution_margin.value is not None
            and assumptions.gross_margin.value is not None
            and abs(assumptions.contribution_margin.value - assumptions.gross_margin.value) < 1e-9
        )
        if contribution_equals_gross:
            contribution = derived_margin
            unknowns.pop("contribution_margin", None)
            adjustments["contribution_margin"] = "derived_from_price_and_variable_cost"
    elif price == 0:
        gross = None
        unknowns["gross_margin"] = "Gross margin is undefined when price is zero."
    contribution = None if contribution is None else min(1.0, contribution)
    gross = None if gross is None else min(1.0, gross)

    adds = leads * conversion if leads is not None and conversion is not None else None
    if adds is None:
        unknowns["new_customers_per_month"] = "Qualified leads and conversion rate are both required."
    customers = revenue = None
    if start is not None and adds is not None and retention is not None:
        count = start
        revenue = 0.0 if price is not None else None
        for _ in range(assumptions.period_months):
            count = count * max(0.0, min(1.0, retention)) + adds
            if revenue is not None:
                revenue += count * price
        customers = count
        if price is None:
            unknowns["revenue"] = "Monthly price is unknown."
    elif "customers_at_start" not in unknowns:
        unknowns["revenue"] = "New customer growth or retention is unknown."
    if price is None or contribution is None or lifetime is None:
        ltv = None
        unknowns["ltv"] = "Monthly price, contribution margin, and lifetime are required."
    else:
        ltv = price * contribution * lifetime
    if adds is None or spend is None:
        cac = None
        unknowns["cac"] = "Acquisition spend and acquired customer count are required."
    elif adds == 0:
        cac = None
        unknowns["cac"] = "CAC is undefined when no new customers are acquired."
    else:
        cac = spend / adds
    break_even_customers = None
    if fixed is not None and price is not None and (contribution is not None or variable is not None):
        unit_contribution = price * contribution if contribution is not None else price - variable
        if unit_contribution > 0:
            break_even_customers = fixed / unit_contribution
        else:
            unknowns["break_even_customers"] = "Unit contribution is zero or negative."
    else:
        unknowns["break_even_customers"] = "Fixed costs and price plus contribution margin or variable cost are required."
    break_even_revenue = (
        break_even_customers * price
        if break_even_customers is not None and price is not None
        else None
    )
    payback = None
    if investment is not None and fixed is not None and spend is not None and customers is not None and price is not None and (contribution is not None or variable is not None):
        unit_contribution = price * contribution if contribution is not None else price - variable
        monthly_surplus = customers * unit_contribution - fixed - spend
        if monthly_surplus > 0:
            payback = investment / monthly_surplus
        else:
            unknowns["payback_months"] = "Projected monthly operating surplus is not positive."
    else:
        unknowns["payback_months"] = "Investment, acquisition spend, and projected operating surplus are required."
    return ScenarioResult(
        name=name, ending_customers=customers, revenue=revenue, cac=cac, ltv=ltv,
        gross_margin=None if gross is None else min(1.0, gross),
        contribution_margin=None if contribution is None else min(1.0, contribution),
        break_even_customers=break_even_customers, break_even_revenue=break_even_revenue,
        initial_investment=investment, payback_months=payback,
        first_revenue_month=first, scenario_adjustments=adjustments, unknowns=unknowns,
    )


def calculate_economics(assumptions: CommercialAssumptions) -> CommercialEconomics:
    """Calculate three fixed sensitivity cases without inference or side effects."""
    return CommercialEconomics(
        currency=assumptions.currency, period_months=assumptions.period_months,
        assumptions=assumptions,
        scenarios={
            "pessimistic": _scenario(assumptions, "pessimistic"),
            "base": _scenario(assumptions, "base"),
            "optimistic": _scenario(assumptions, "optimistic"),
        },
    )


class CommercialEvidenceGrade(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assumption_id: str
    coverage: float = Field(ge=0, le=1)
    independent_sources: int = Field(ge=0)
    supporting_grade: CommercialEvidenceClass
    contradicting_grade: CommercialEvidenceClass
    product_supporting_grade: CommercialEvidenceClass = CommercialEvidenceClass.UNKNOWN
    market_supporting_grade: CommercialEvidenceClass = CommercialEvidenceClass.UNKNOWN
    supporting_confidence: float = Field(default=0, ge=0, le=1)
    contradicting_confidence: float = Field(default=0, ge=0, le=1)
    product_supporting_confidence: float = Field(default=0, ge=0, le=1)
    market_supporting_confidence: float = Field(default=0, ge=0, le=1)
    evidence_ids: list[str]
    unknown_ids: list[str] = Field(default_factory=list)


def grade_commercial_evidence(
    assumption_ids: Iterable[str], evidence: Iterable[EvidenceItem],
) -> list[CommercialEvidenceGrade]:
    """Grade recorded metadata; references to one publisher/root count once."""
    items = list(evidence)
    weights = {
        CommercialEvidenceClass.MARKET_SIGNAL: 1,
        CommercialEvidenceClass.EXISTING_MARKET: 2,
        CommercialEvidenceClass.CUSTOMER_VALIDATION: 3,
        CommercialEvidenceClass.PURCHASE_INTENT: 4,
        CommercialEvidenceClass.OBSERVED_TRANSACTION: 5,
        CommercialEvidenceClass.UNKNOWN: 0,
    }
    tier_quality = {
        EvidenceTier.SECONDARY: 0.7,
        EvidenceTier.PRIMARY: 0.85,
        EvidenceTier.OBSERVED_BEHAVIOR: 1.0,
        EvidenceTier.MODEL_ONLY: 0.0,
    }
    type_quality = {
        EvidenceType.OBSERVED: 1.0,
        EvidenceType.MEASURED: 1.0,
        EvidenceType.INFERRED: 0.7,
        EvidenceType.UNKNOWN: 0.0,
        EvidenceType.MODEL_JUDGMENT: 0.0,
    }
    grades = []
    for assumption_id in assumption_ids:
        matched = [item for item in items if assumption_id in item.supported_assumption_ids]
        eligible = [
            item for item in matched
            if item.tier is not EvidenceTier.MODEL_ONLY
            and item.evidence_type is not EvidenceType.MODEL_JUDGMENT
        ]
        by_lineage: dict[str, list[EvidenceItem]] = {}
        alias_to_group: dict[str, str] = {}
        for item in eligible:
            source = item.source_identifier.strip().lower().rstrip("/")
            aliases = [f"lineage:{item.lineage_group_id}", f"source:{source}"]
            group = next((alias_to_group[alias] for alias in aliases if alias in alias_to_group), item.lineage_group_id)
            by_lineage.setdefault(group, []).append(item)
            for alias in aliases:
                alias_to_group[alias] = group
        independent = [item for lineage_items in by_lineage.values() for item in lineage_items]
        def best(direction: EvidenceDirection) -> CommercialEvidenceClass:
            candidates = [item.commercial_classification for item in independent if item.direction is direction]
            return max(candidates, key=lambda grade: weights[grade], default=CommercialEvidenceClass.UNKNOWN)
        known_lineages = sum(
            any(item.commercial_classification is not CommercialEvidenceClass.UNKNOWN for item in lineage_items)
            for lineage_items in by_lineage.values()
        )
        def scoped_best(scope: str) -> CommercialEvidenceClass:
            candidates = [item.commercial_classification for item in independent if item.commercial_scope.value == scope and item.direction is EvidenceDirection.SUPPORTS]
            return max(candidates, key=lambda grade: weights[grade], default=CommercialEvidenceClass.UNKNOWN)
        def confidence(direction: EvidenceDirection, scope: str | None = None) -> float:
            source_scores = []
            for lineage_items in by_lineage.values():
                candidates = [
                    item.reliability_score * item.freshness_score * tier_quality[item.tier]
                    * type_quality[item.evidence_type] * weights[item.commercial_classification] / 5
                    for item in lineage_items
                    if item.direction is direction
                    and (scope is None or item.commercial_scope.value == scope)
                ]
                if candidates:
                    source_scores.append(max(candidates))
            return 1 - prod(1 - score for score in sorted(source_scores))
        grades.append(CommercialEvidenceGrade(
            assumption_id=assumption_id,
            coverage=1.0 if known_lineages else 0.0,
            independent_sources=known_lineages,
            supporting_grade=best(EvidenceDirection.SUPPORTS),
            contradicting_grade=best(EvidenceDirection.CONTRADICTS),
            product_supporting_grade=scoped_best("PRODUCT"),
            market_supporting_grade=scoped_best("MARKET"),
            supporting_confidence=confidence(EvidenceDirection.SUPPORTS),
            contradicting_confidence=confidence(EvidenceDirection.CONTRADICTS),
            product_supporting_confidence=confidence(EvidenceDirection.SUPPORTS, "PRODUCT"),
            market_supporting_confidence=confidence(EvidenceDirection.SUPPORTS, "MARKET"),
            evidence_ids=sorted({item.id for item in matched}),
            unknown_ids=sorted({item.id for item in matched if item.commercial_classification is CommercialEvidenceClass.UNKNOWN}),
        ))
    return grades
