from axiomai.application.exceptions.common import AppError


class PaymentNotFoundError(AppError):
    """Exception raised when a payment is not found."""


class PaymentAlreadyProcessedError(AppError):
    """Exception raised when attempting to process a payment that has already been processed."""


class NotEnoughBalanceError(AppError):
    """Exception raised when there is not enough balance to process a payment."""
