from pydantic import BaseModel, ConfigDict, Field


class ModelCapabilities(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str
    context_tokens: int = Field(gt=0)
    reasoning: bool
    tools: bool
    structured_output: bool


class ProviderHealth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    reachable: bool
    version: str | None = None
    installed_models: list[str] = Field(default_factory=list)
    error: str | None = None
