from pathlib import Path

from dbie.config import load_models_config, load_settings
from dbie.models.roles import ModelRole


def test_requested_ollama_models_are_exact() -> None:
    settings = load_settings()
    models = load_models_config(settings)

    assert settings.web_viewer.host == "0.0.0.0"
    assert settings.web_viewer.runs_dir == Path("runs")
    assert settings.web_viewer.auto_refresh_seconds == 3
    assert models.active_provider == "ollama"
    assert models.profiles[models.default_profile].model == "gpt-oss:20b-64k"
    assert [models.profiles[name].model for name in models.fallback_profiles] == [
        "ministral-3:14b-64k"
    ]


def test_environment_overrides_yaml(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "override.sqlite3"
    monkeypatch.setenv("DBIE_DATABASE_URL", f"sqlite:///{target}")

    settings = load_settings()

    assert settings.database_url == f"sqlite:///{target}"


def test_specialized_model_roles_are_configuration_not_crew_logic() -> None:
    models = load_models_config(load_settings())

    assert models.profiles[models.roles[ModelRole.THINKER].primary_profile].model == (
        "ministral-3:14b-64k"
    )
    assert models.profiles[models.roles[ModelRole.DOER].primary_profile].model == (
        "qwen3:14b-64k"
    )
    assert models.profiles[models.roles[ModelRole.BUILDER].primary_profile].model == (
        "qwen3:14b-64k"
    )
    assert models.profiles[models.roles[ModelRole.JUDGE].primary_profile].model == (
        "gpt-oss:20b-64k"
    )
