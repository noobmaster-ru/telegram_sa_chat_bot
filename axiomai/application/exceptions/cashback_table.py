from axiomai.application.exceptions.common import AppError


class WritePermissionError(AppError):
    """Raised when there is no write permission for cashback table."""


class CashbackTableAlredyExistsError(AppError):
    """Raised when cashback table already exists."""


class CashbackTableNotFoundError(AppError):
    """Raised when cashback table is not found."""
