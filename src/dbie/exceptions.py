"""Application exception hierarchy."""


class DBIEError(Exception):
    """Base exception for expected DBIE failures."""


class ConfigurationError(DBIEError):
    """Configuration is missing or invalid."""


class PersistenceError(DBIEError):
    """Durable state could not be read or written."""


class DomainRuleViolation(DBIEError):
    """A deterministic domain rule rejected an operation."""


class InvalidStateTransition(DomainRuleViolation):
    """A candidate lifecycle transition is not allowed."""


class ModelProviderError(DBIEError):
    """A model provider request failed."""


class ModelUnavailableError(ModelProviderError):
    """A configured model is not available from its provider."""


class StructuredOutputError(ModelProviderError):
    """A model response failed schema validation."""


class ToolGatewayError(DBIEError):
    """A logical tool request was rejected or failed safely."""


class ToolPermissionDenied(ToolGatewayError):
    """The actor is not authorized to use the requested logical tool."""


class ToolBudgetExceeded(ToolGatewayError):
    """The request exceeded a deterministic tool budget."""


class ToolExecutionError(ToolGatewayError):
    """An internal adapter failed without leaking provider details."""


class ToolInputValidationError(ToolGatewayError):
    """Logical tool arguments failed their stable typed contract."""
