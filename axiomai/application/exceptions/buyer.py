from axiomai.application.exceptions.common import AppError


class BuyerNotFoundError(AppError):
    """Exception raised when a buyer is not found."""


class BuyerAlreadyOrderedError(AppError):
    """Exception raised when attempting to cancel a buyer that already submitted an order screenshot."""
