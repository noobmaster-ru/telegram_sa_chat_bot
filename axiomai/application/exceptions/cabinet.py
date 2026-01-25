from axiomai.application.exceptions.common import AppError


class CabinetAlreadyExistsError(AppError):
    """Exception raised when attempting to create a cabinet that already exists."""


class CabinetNotFoundError(AppError):
    """Exception raised when a cabinet is not found."""


class BusinessAccountAlreadyLinkedError(AppError):
    """Exception raised when a business account is already linked to a cabinet."""
