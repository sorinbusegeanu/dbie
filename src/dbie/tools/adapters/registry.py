from dbie.tools.adapters.base import AdapterHealth, ToolAdapter


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, ToolAdapter] = {}

    def register(self, adapter: ToolAdapter) -> None:
        if adapter.name in self._adapters:
            raise ValueError(f"adapter already registered: {adapter.name}")
        self._adapters[adapter.name] = adapter

    def get(self, name: str) -> ToolAdapter:
        try:
            return self._adapters[name]
        except KeyError as exc:
            raise KeyError(f"adapter not registered: {name}") from exc

    def health(self) -> list[AdapterHealth]:
        return [self._adapters[name].health() for name in sorted(self._adapters)]

    def names(self) -> set[str]:
        return set(self._adapters)
