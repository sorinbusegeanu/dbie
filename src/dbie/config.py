"""Typed configuration loading with environment overrides."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from dbie.exceptions import ConfigurationError
from dbie.domain.decisions import ReadinessPolicy
from dbie.models.roles import ModelRole
from dbie.models.task_roles import TaskClass


class OllamaSettings(BaseModel):
    base_url: str = "http://127.0.0.1:11434"
    timeout_seconds: float = 180.0
    keep_alive: str = "5m"


class ModelProfile(BaseModel):
    provider: str
    model: str
    family: str
    maximum_context_tokens: int = Field(gt=0)
    request_context_tokens: int = Field(gt=0)
    maximum_output_tokens: int = Field(default=8192, gt=0)
    reasoning: bool = False
    tools: bool = False
    structured_output: bool = False
    active_concurrency: int = Field(default=1, ge=1)


class ModelRoleConfig(BaseModel):
    primary_profile: str
    challenger_profile: str | None = None
    fallback_profiles: list[str] = Field(default_factory=list)
    context_tokens: int = Field(gt=0)
    thinking_mode: str = "adaptive"
    challenger_fraction: float = Field(default=0, ge=0, le=1)

    def model_post_init(self, __context: Any, /) -> None:
        allowed = {"off", "low", "medium", "high", "adaptive"}
        if self.thinking_mode not in allowed:
            raise ValueError(f"unknown thinking mode: {self.thinking_mode}")


class ModelsConfig(BaseModel):
    active_provider: str
    default_profile: str
    fallback_profiles: list[str] = Field(default_factory=list)
    providers: dict[str, OllamaSettings]
    profiles: dict[str, ModelProfile]
    roles: dict[ModelRole, ModelRoleConfig] = Field(default_factory=dict)
    task_temperatures: dict[TaskClass, float] = Field(default_factory=dict)

    def model_post_init(self, __context: Any, /) -> None:
        names = [self.default_profile, *self.fallback_profiles]
        missing = [name for name in names if name not in self.profiles]
        if missing:
            raise ValueError(f"unknown model profiles: {', '.join(missing)}")
        for name, profile in self.profiles.items():
            if profile.request_context_tokens > profile.maximum_context_tokens:
                raise ValueError(
                    f"profile {name} request context exceeds maximum context"
                )
        for role, mapping in self.roles.items():
            role_profiles = [
                mapping.primary_profile,
                *mapping.fallback_profiles,
                *([mapping.challenger_profile] if mapping.challenger_profile else []),
            ]
            unknown = [name for name in role_profiles if name not in self.profiles]
            if unknown:
                raise ValueError(
                    f"role {role.value} references unknown profiles: {', '.join(unknown)}"
                )
            if (
                mapping.context_tokens
                > self.profiles[mapping.primary_profile].maximum_context_tokens
            ):
                raise ValueError(
                    f"role {role.value} context exceeds its primary profile maximum"
                )
        if any(not 0 <= value <= 2 for value in self.task_temperatures.values()):
            raise ValueError("task temperatures must be between 0 and 2")


class WebViewerSettings(BaseModel):
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = Field(default=8080, ge=1, le=65535)
    runs_dir: Path = Path("runs")
    current_run: str = "current"
    auto_refresh_seconds: int = Field(default=3, ge=0, le=60)
    max_text_bytes: int = Field(default=5_000_000, ge=1)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DBIE_",
        env_file=".env",
        extra="ignore",
    )

    environment: str = "local"
    database_url: str = "sqlite:///runs/dbie.sqlite3"
    run_directory: Path = Path("runs")
    log_level: str = "INFO"
    json_logs: bool = False
    models_config: Path = Path("config/models.yaml")
    tools_config: Path = Path("config/tools.yaml")
    policies_config: Path = Path("config/policies.yaml")
    web_viewer: WebViewerSettings = Field(default_factory=WebViewerSettings)


def _yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError as exc:
        raise ConfigurationError(f"cannot read configuration {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"invalid YAML in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ConfigurationError(f"configuration root must be a mapping: {path}")
    return value


def load_settings(path: Path | str = Path("config/default.yaml")) -> Settings:
    config_path = Path(path)
    data = _yaml_mapping(config_path)
    for field_name in Settings.model_fields:
        environment_name = f"DBIE_{field_name.upper()}"
        if environment_name in os.environ:
            data[field_name] = os.environ[environment_name]
    try:
        return Settings(**data)
    except ValueError as exc:
        raise ConfigurationError(f"invalid settings in {config_path}: {exc}") from exc


def load_models_config(settings: Settings) -> ModelsConfig:
    data = _yaml_mapping(settings.models_config)
    try:
        return ModelsConfig.model_validate(data)
    except ValueError as exc:
        raise ConfigurationError(
            f"invalid model configuration in {settings.models_config}: {exc}"
        ) from exc


def load_tools_config(settings: Settings) -> dict[str, Any]:
    return _yaml_mapping(settings.tools_config)


def load_readiness_policy(settings: Settings) -> ReadinessPolicy:
    """Load decision thresholds from the existing policies YAML."""
    data = _yaml_mapping(settings.policies_config)
    readiness = data.get("decision_readiness", {})
    if not isinstance(readiness, dict):
        raise ConfigurationError("decision_readiness policy must be a mapping")
    try:
        return ReadinessPolicy.model_validate(readiness)
    except ValueError as exc:
        raise ConfigurationError(f"invalid decision_readiness policy: {exc}") from exc


def load_opportunity_memory_policy(settings: Settings) -> dict[str, Any]:
    data = _yaml_mapping(settings.policies_config)
    policy = data.get("opportunity_memory", {})
    if not isinstance(policy, dict):
        raise ConfigurationError("opportunity_memory policy must be a mapping")
    threshold = float(policy.get("duplicate_similarity_threshold", 0.55))
    retrieval_similarity = float(policy.get("minimum_retrieval_similarity", 0.15))
    retrieval_limit = int(policy.get("retrieval_limit", 5))
    if not 0.1 <= threshold <= 1 or not -1 <= retrieval_similarity <= 1 or not 1 <= retrieval_limit <= 100:
        raise ConfigurationError("invalid opportunity_memory threshold or result limit")
    return {
        "duplicate_similarity_threshold": threshold,
        "minimum_retrieval_similarity": retrieval_similarity,
        "retrieval_limit": retrieval_limit,
    }
