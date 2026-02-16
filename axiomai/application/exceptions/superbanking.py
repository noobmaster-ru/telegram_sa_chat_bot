from axiomai.application.exceptions.common import AppError


class CreatePaymentError(AppError):
    """Exception raised when Superbanking payment creation fails."""


class SignPaymentError(AppError):
    """Exception raised when Superbanking payment signing fails."""


class SkipSuperbankingError(AppError):
    """When is_superbanking_connect is False, this exception will raise"""

    def __init__(self, cabinet_id: int, *, is_superbanking_connect: bool) -> None:
        self.cabinet_id = cabinet_id
        self.is_superbanking_connect = is_superbanking_connect
