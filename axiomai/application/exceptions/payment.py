from axiomai.application.exceptions.common import AppError


class PaymentNotFoundError(AppError):
    """Exception raised when a payment is not found."""


class PaymentAlreadyProcessedError(AppError):
    """Exception raised when attempting to process a payment that has already been processed."""


class PermissionDeniedError(AppError):
    """Exception raised when user does not have permission to perform an action."""
