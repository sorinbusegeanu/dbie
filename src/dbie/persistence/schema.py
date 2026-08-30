"""Initial relational schema with versioned JSON payloads."""

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
)

metadata = MetaData()

runs = Table(
    "runs",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("status", String(32), nullable=False, index=True),
    Column("mandate", Text, nullable=False),
    Column("schema_version", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("payload", JSON, nullable=False),
)

ideas = Table(
    "business_ideas",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("run_id", String(36), nullable=False, index=True),
    Column("problem_id", String(128), nullable=False, index=True),
    Column("state", String(32), nullable=False, index=True),
    Column("schema_version", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("payload", JSON, nullable=False),
)

assumptions = Table(
    "assumptions",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("run_id", String(36), nullable=False, index=True),
    Column("idea_id", String(36), nullable=False, index=True),
    Column("category", String(32), nullable=False),
    Column("criticality", String(32), nullable=False),
    Column("status", String(32), nullable=False),
    Column("schema_version", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("payload", JSON, nullable=False),
)

evidence = Table(
    "evidence_items",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("run_id", String(36), nullable=False, index=True),
    Column("lineage_group_id", String(128), nullable=False, index=True),
    Column("content_hash", String(128), nullable=False),
    Column("tier", String(32), nullable=False),
    Column("schema_version", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("payload", JSON, nullable=False),
    UniqueConstraint(
        "content_hash", "lineage_group_id", name="uq_evidence_content_lineage"
    ),
)

events = Table(
    "domain_events",
    metadata,
    Column("sequence", Integer, primary_key=True, autoincrement=True),
    Column("event_id", String(36), nullable=False, unique=True),
    Column("run_id", String(36), nullable=False, index=True),
    Column("entity_type", String(64), nullable=False),
    Column("entity_id", String(36), nullable=False, index=True),
    Column("event_type", String(64), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("payload", JSON, nullable=False),
)

semantic_memories = Table(
    "semantic_memories",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("run_id", String(36), nullable=False, index=True),
    Column("entity_type", String(64), nullable=False, index=True),
    Column("entity_id", String(36), nullable=False, index=True),
    Column("canonical_text", Text, nullable=False),
    Column("embedding", JSON, nullable=False),
    Column("embedding_model", String(256), nullable=False),
    Column("embedding_dimension", Integer, nullable=False),
    Column("normalization_version", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint(
        "entity_type",
        "entity_id",
        "embedding_model",
        "normalization_version",
        name="uq_semantic_memory_version",
    ),
)

pairwise_matches = Table(
    "pairwise_matches",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("run_id", String(36), nullable=False, index=True),
    Column("left_idea_id", String(36), nullable=False, index=True),
    Column("right_idea_id", String(36), nullable=False, index=True),
    Column("winner_idea_id", String(36), nullable=True),
    Column("judge_model", String(256), nullable=False),
    Column("schema_version", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("payload", JSON, nullable=False),
)

experiments = Table(
    "experiments",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("run_id", String(36), nullable=False, index=True),
    Column("idea_id", String(36), nullable=False, index=True),
    Column("assumption_id", String(36), nullable=False, index=True),
    Column("approval_status", String(32), nullable=False, index=True),
    Column("protocol_version", Integer, nullable=False),
    Column("schema_version", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("payload", JSON, nullable=False),
)

experiment_predictions = Table(
    "experiment_predictions",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("run_id", String(36), nullable=False, index=True),
    Column("experiment_id", String(36), nullable=False, index=True),
    Column("schema_version", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("payload", JSON, nullable=False),
)

experiment_outcomes = Table(
    "experiment_outcomes",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("run_id", String(36), nullable=False, index=True),
    Column("experiment_id", String(36), nullable=False, index=True),
    Column("schema_version", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("payload", JSON, nullable=False),
)

evaluations = Table(
    "evaluations",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("run_id", String(36), nullable=False, index=True),
    Column("idea_id", String(36), nullable=False, index=True),
    Column("evaluator_actor_id", String(128), nullable=False),
    Column("recommendation", String(32), nullable=False),
    Column("schema_version", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("payload", JSON, nullable=False),
)

model_performance_records = Table(
    "model_performance_records",
    metadata,
    Column("model_run_id", String(36), primary_key=True),
    Column("run_id", String(36), nullable=False, index=True),
    Column("venture_id", String(36), nullable=True, index=True),
    Column("crew_id", String(128), nullable=False, index=True),
    Column("agent_id", String(128), nullable=False, index=True),
    Column("task_id", String(128), nullable=False, index=True),
    Column("task_class", String(64), nullable=False, index=True),
    Column("model_role", String(16), nullable=False, index=True),
    Column("model_id", String(256), nullable=False, index=True),
    Column("task_success", String(8), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("payload", JSON, nullable=False),
)

model_phase_performance_records = Table(
    "model_phase_performance_records",
    metadata,
    Column("phase_run_id", String(36), primary_key=True),
    Column("run_id", String(36), nullable=False, index=True),
    Column("phase_id", String(32), nullable=False, index=True),
    Column("model_role", String(16), nullable=False, index=True),
    Column("model_id", String(256), nullable=False, index=True),
    Column("dependency_barrier", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("payload", JSON, nullable=False),
)
