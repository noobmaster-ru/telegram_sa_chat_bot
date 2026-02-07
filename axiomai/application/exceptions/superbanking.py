from axiomai.application.exceptions.common import AppError


class CreatePaymentError(AppError):
    """Exception raised when Superbanking payment creation fails."""


class SignPaymentError(AppError):
    """Exception raised when Superbanking payment signing fails."""
