"""Configuration-driven model routing and fallback."""

from __future__ import annotations

from hashlib import sha256

from pydantic import BaseModel

from dbie.config import ModelsConfig
from dbie.exceptions import ModelProviderError, ModelUnavailableError
from dbie.models.base import GenerationRequest, GenerationResponse, LLMProvider, SchemaT
from dbie.models.roles import ModelRole, ModelSelection


class RoleResolution(BaseModel):
    role: ModelRole
    selection: ModelSelection
    profile_name: str
    model_id: str
    thinking_mode: str
    context_tokens: int


class ModelRouter:
    def __init__(
        self,
        config: ModelsConfig,
        providers: dict[str, LLMProvider],
    ) -> None:
        self.config = config
        self.providers = providers

    def generate(
        self,
        request: GenerationRequest,
        *,
        profile_name: str | None = None,
        allow_fallback: bool = True,
    ) -> GenerationResponse:
        errors: list[str] = []
        for name in self._profile_order(profile_name, allow_fallback):
            profile = self.config.profiles[name]
            provider = self._provider(profile.provider)
            try:
                return provider.generate(profile.model, request)
            except ModelProviderError as exc:
                errors.append(f"{name}: {exc}")
        raise ModelUnavailableError(
            "all routed model attempts failed: " + "; ".join(errors)
        )

    def structured_generate(
        self,
        request: GenerationRequest,
        schema: type[SchemaT],
        *,
        profile_name: str | None = None,
        allow_fallback: bool = True,
    ) -> SchemaT:
        errors: list[str] = []
        for name in self._profile_order(profile_name, allow_fallback):
            profile = self.config.profiles[name]
            provider = self._provider(profile.provider)
            try:
                return provider.structured_generate(profile.model, request, schema)
            except ModelProviderError as exc:
                errors.append(f"{name}: {exc}")
        raise ModelUnavailableError(
            "all routed model attempts failed: " + "; ".join(errors)
        )

    def tool_call(
        self,
        request: GenerationRequest,
        *,
        profile_name: str | None = None,
        allow_fallback: bool = True,
    ) -> GenerationResponse:
        errors: list[str] = []
        for name in self._profile_order(profile_name, allow_fallback):
            profile = self.config.profiles[name]
            provider = self._provider(profile.provider)
            try:
                return provider.tool_call(profile.model, request)
            except ModelProviderError as exc:
                errors.append(f"{name}: {exc}")
        raise ModelUnavailableError(
            "all routed tool-call attempts failed: " + "; ".join(errors)
        )

    def resolve_role(
        self,
        role: ModelRole,
        *,
        selection: ModelSelection = ModelSelection.PRIMARY,
    ) -> RoleResolution:
        try:
            mapping = self.config.roles[role]
        except KeyError as exc:
            raise ModelUnavailableError(
                f"model role is not configured: {role.value}"
            ) from exc
        profile_name = mapping.primary_profile
        if selection is ModelSelection.CHALLENGER:
            if mapping.challenger_profile is None:
                raise ModelUnavailableError(
                    f"model role has no challenger: {role.value}"
                )
            profile_name = mapping.challenger_profile
        return RoleResolution(
            role=role,
            selection=selection,
            profile_name=profile_name,
            model_id=self.config.profiles[profile_name].model,
            thinking_mode=(
                mapping.thinking_mode
                if self.config.profiles[profile_name].reasoning
                else "off"
            ),
            context_tokens=mapping.context_tokens,
        )

    def selection_for_task(self, role: ModelRole, task_id: str) -> ModelSelection:
        try:
            fraction = self.config.roles[role].challenger_fraction
        except KeyError as exc:
            raise ModelUnavailableError(
                f"model role is not configured: {role.value}"
            ) from exc
        if not fraction or self.config.roles[role].challenger_profile is None:
            return ModelSelection.PRIMARY
        bucket = int.from_bytes(sha256(task_id.encode()).digest()[:8], "big") / 2**64
        return (
            ModelSelection.CHALLENGER if bucket < fraction else ModelSelection.PRIMARY
        )

    def generate_for_role(
        self,
        request: GenerationRequest,
        *,
        role: ModelRole,
        selection: ModelSelection = ModelSelection.PRIMARY,
        allow_fallback: bool = True,
    ) -> GenerationResponse:
        errors: list[str] = []
        for name in self._role_profile_order(role, selection, allow_fallback):
            profile = self.config.profiles[name]
            prepared = self._prepare_role_request(request, role, name)
            try:
                return self._provider(profile.provider).generate(
                    profile.model, prepared
                )
            except ModelProviderError as exc:
                errors.append(f"{name}: {exc}")
        raise ModelUnavailableError(
            f"all {role.value} model attempts failed: " + "; ".join(errors)
        )

    def structured_generate_for_role(
        self,
        request: GenerationRequest,
        schema: type[SchemaT],
        *,
        role: ModelRole,
        selection: ModelSelection = ModelSelection.PRIMARY,
        allow_fallback: bool = True,
    ) -> SchemaT:
        errors: list[str] = []
        for name in self._role_profile_order(role, selection, allow_fallback):
            profile = self.config.profiles[name]
            prepared = self._prepare_role_request(request, role, name)
            try:
                return self._provider(profile.provider).structured_generate(
                    profile.model, prepared, schema
                )
            except ModelProviderError as exc:
                errors.append(f"{name}: {exc}")
        raise ModelUnavailableError(
            f"all {role.value} structured model attempts failed: " + "; ".join(errors)
        )

    def tool_call_for_role(
        self,
        request: GenerationRequest,
        *,
        role: ModelRole,
        selection: ModelSelection = ModelSelection.PRIMARY,
        allow_fallback: bool = True,
    ) -> GenerationResponse:
        errors: list[str] = []
        for name in self._role_profile_order(role, selection, allow_fallback):
            profile = self.config.profiles[name]
            prepared = self._prepare_role_request(request, role, name)
            try:
                return self._provider(profile.provider).tool_call(
                    profile.model, prepared
                )
            except ModelProviderError as exc:
                errors.append(f"{name}: {exc}")
        raise ModelUnavailableError(
            f"all {role.value} tool-call attempts failed: " + "; ".join(errors)
        )

    def _profile_order(self, requested: str | None, allow_fallback: bool) -> list[str]:
        primary = requested or self.config.default_profile
        if primary not in self.config.profiles:
            raise ModelUnavailableError(f"unknown model profile: {primary}")
        names = [primary]
        if allow_fallback:
            names.extend(
                name for name in self.config.fallback_profiles if name != primary
            )
        return names

    def _provider(self, name: str) -> LLMProvider:
        try:
            return self.providers[name]
        except KeyError as exc:
            raise ModelUnavailableError(f"provider not configured: {name}") from exc

    def _role_profile_order(
        self,
        role: ModelRole,
        selection: ModelSelection,
        allow_fallback: bool,
    ) -> list[str]:
        mapping = self.config.roles[role]
        first = self.resolve_role(role, selection=selection).profile_name
        names = [first]
        if selection is ModelSelection.CHALLENGER:
            names.append(mapping.primary_profile)
        if allow_fallback:
            names.extend(mapping.fallback_profiles)
        return list(dict.fromkeys(names))

    def _prepare_role_request(
        self,
        request: GenerationRequest,
        role: ModelRole,
        profile_name: str,
    ) -> GenerationRequest:
        mapping = self.config.roles[role]
        changes: dict[str, object] = {}
        if request.context_tokens is None:
            changes["context_tokens"] = mapping.context_tokens
        if not self.config.profiles[profile_name].reasoning:
            changes["thinking"] = False
            changes["reasoning_effort"] = None
        elif request.thinking is None and request.reasoning_effort is None:
            if mapping.thinking_mode == "off":
                changes["thinking"] = False
            elif mapping.thinking_mode in {"low", "medium", "high"}:
                changes["reasoning_effort"] = mapping.thinking_mode
        return request.model_copy(update=changes)
