"""Application object construction kept outside CLI and CrewAI layers."""

from dataclasses import dataclass

from dbie.config import ModelsConfig, Settings, load_models_config, load_settings
from dbie.crews.router_llm import RouterLLM
from dbie.models.ollama_provider import OllamaProvider
from dbie.models.router import ModelRouter
from dbie.persistence.db import Database
from dbie.persistence.model_performance import ModelPerformanceRepository


@dataclass
class Runtime:
    settings: Settings
    models_config: ModelsConfig
    database: Database
    ollama: OllamaProvider
    router: ModelRouter
    crew_llm: RouterLLM
    model_performance: ModelPerformanceRepository


def build_runtime(config_path: str = "config/default.yaml") -> Runtime:
    settings = load_settings(config_path)
    models_config = load_models_config(settings)
    database = Database(settings.database_url)
    ollama_settings = models_config.providers["ollama"]
    ollama = OllamaProvider(ollama_settings, models_config.profiles)
    router = ModelRouter(models_config, {"ollama": ollama})
    model_performance = ModelPerformanceRepository(database)
    return Runtime(
        settings=settings,
        models_config=models_config,
        database=database,
        ollama=ollama,
        router=router,
        crew_llm=RouterLLM(router, performance_sink=model_performance),
        model_performance=model_performance,
    )
