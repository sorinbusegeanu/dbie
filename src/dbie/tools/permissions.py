from dbie.tools.contracts import ToolName


class ToolPermissionPolicy:
    def __init__(self, actor_permissions: dict[str, list[str]]) -> None:
        self.actor_permissions = {
            actor: {ToolName(name) for name in names}
            for actor, names in actor_permissions.items()
        }

    def allowed(self, actor_id: str, tool: ToolName) -> bool:
        return tool in self.actor_permissions.get(actor_id, set())
