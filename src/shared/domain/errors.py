class DomainError(Exception):
    """Erro de regra de negócio."""


class NotFoundError(DomainError):
    pass


class UnauthorizedError(DomainError):
    pass


class ForbiddenError(DomainError):
    pass


class FeatureLockedError(DomainError):
    """Recurso bloqueado por entitlement — o front usa a feature_key p/ renderizar o upsell."""

    def __init__(self, feature_key: str) -> None:
        super().__init__(f"Recurso bloqueado: {feature_key}")
        self.feature_key = feature_key
