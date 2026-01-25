from axiomai.application.exceptions.common import AppError


class UserAlreadyExistsError(AppError):
    """Exception raised when attempting to create a user that already exists."""


class UserNotFoundError(AppError):
    """Exception raised when a user is not found."""
