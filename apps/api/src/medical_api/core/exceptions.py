class DomainError(Exception):
    """Base class for domain/business-rule errors raised by services."""


class NotFoundError(DomainError):
    def __init__(self, resource: str, resource_id: object):
        self.resource = resource
        self.resource_id = resource_id
        super().__init__(f"{resource} {resource_id} not found")


class ConflictError(DomainError):
    pass


class PermissionDeniedError(DomainError):
    pass


class RateLimitedError(DomainError):
    pass
