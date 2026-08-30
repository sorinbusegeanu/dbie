from dbie.config import load_settings, load_tools_config
from dbie.crews.catalog import (
    BUILDER_SPECS,
    DISCOVERY_SPECS,
    IDEATION_SPECS,
    RED_TEAM_SPECS,
    SYNTHESIS_SPECS,
    VALIDATION_SPECS,
    actor_id_for,
    deduplicate_idea_theses,
    exploration_allocation,
)
from dbie.crews.model_roles import TASK_MODEL_ROLES, TaskClass
from dbie.models.roles import ModelRole
from dbie.tools.permissions import ToolPermissionPolicy


def test_phase8_actor_catalog_separates_generation_and_evaluation() -> None:
    generator_roles = {item.role for item in IDEATION_SPECS}
    evaluator_roles = {item.role for item in VALIDATION_SPECS + RED_TEAM_SPECS}

    assert len(DISCOVERY_SPECS) == 6
    assert len(IDEATION_SPECS) == 8
    assert not generator_roles & evaluator_roles
    assert {item.model_role for item in DISCOVERY_SPECS} == {ModelRole.DOER}
    assert {item.model_role for item in IDEATION_SPECS + SYNTHESIS_SPECS} == {
        ModelRole.THINKER
    }
    assert {item.model_role for item in BUILDER_SPECS} == {ModelRole.BUILDER}
    assert {item.model_role for item in RED_TEAM_SPECS} == {ModelRole.JUDGE}


def test_exploration_budget_is_in_required_band() -> None:
    exploitation, exploration = exploration_allocation(50)
    assert (exploitation, exploration) == (40, 10)


def test_idea_deduplication_is_stable_and_case_insensitive() -> None:
    assert deduplicate_idea_theses(
        ["Automate AP", " automate   ap ", "Audit APIs"]
    ) == [
        "Automate AP",
        "Audit APIs",
    ]


def test_every_actor_tool_is_allowed_by_external_policy() -> None:
    config = load_tools_config(load_settings())
    policy = ToolPermissionPolicy(config["actor_permissions"])
    for spec in (
        DISCOVERY_SPECS
        + IDEATION_SPECS
        + VALIDATION_SPECS
        + SYNTHESIS_SPECS
        + BUILDER_SPECS
        + RED_TEAM_SPECS
    ):
        actor_id = actor_id_for(spec.role)
        assert all(policy.allowed(actor_id, tool) for tool in spec.tools), actor_id


def test_every_significant_task_class_has_a_specialized_role() -> None:
    assert set(TASK_MODEL_ROLES) == set(TaskClass)
    assert TASK_MODEL_ROLES[TaskClass.EVIDENCE_EXTRACTION] is ModelRole.DOER
    assert TASK_MODEL_ROLES[TaskClass.EVIDENCE_RECONCILIATION] is ModelRole.THINKER
    assert TASK_MODEL_ROLES[TaskClass.TEST_FIX_LOOP] is ModelRole.BUILDER
    assert TASK_MODEL_ROLES[TaskClass.INDEPENDENT_RED_TEAM] is ModelRole.JUDGE


def test_opportunity_synthesizer_requires_a_substantial_description() -> None:
    synthesizer = next(
        item for item in SYNTHESIS_SPECS if item.role == "Opportunity Synthesizer"
    )

    assert "at least 100 words" in synthesizer.goal
