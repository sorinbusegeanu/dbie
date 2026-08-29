from dbie.domain.models import (
    AutonomousScalability,
    BusinessIdea,
    DigitalEligibility,
)


def make_idea(run_id: str = "run-1", **overrides: object) -> BusinessIdea:
    values: dict[str, object] = {
        "run_id": run_id,
        "problem_id": "problem-1",
        "title": "Digital workflow automation",
        "one_sentence_thesis": "Automate a costly digital workflow.",
        "target_customer": "Compliance teams",
        "buyer": "Chief compliance officer",
        "user": "Compliance analyst",
        "value_proposition": "Reduce repetitive review work.",
        "product_form": "SaaS",
        "delivery_model": "Self-service web application",
        "why_now": "New machine-readable regulation",
        "digital_eligibility": DigitalEligibility(
            product_service=True,
            acquisition=True,
            sales=True,
            fulfilment=True,
            operations=True,
            infrastructure=True,
            payments=True,
            support=True,
            scaling=True,
            geography=True,
        ),
        "autonomous_scalability": AutonomousScalability(
            target_automation_ratio=0.9,
            human_minutes_per_customer=20,
            human_minutes_per_customer_at_10x=2,
            human_only_tasks=["approve exception"],
            credible_transition_plan=True,
        ),
    }
    values.update(overrides)
    return BusinessIdea.model_validate(values)
