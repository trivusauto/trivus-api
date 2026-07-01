class DomainError(Exception):
    """Erro de regra de negócio."""


class NotFoundError(DomainError):
    pass


class UnauthorizedError(DomainError):
    pass


class ForbiddenError(DomainError):
    pass
