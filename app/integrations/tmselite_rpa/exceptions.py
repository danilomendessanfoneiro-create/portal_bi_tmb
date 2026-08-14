"""Erros da automação de coleta no TMS Elite (RPA)."""


class TmsRpaError(Exception):
    def __init__(self, message: str, *, step: str) -> None:
        super().__init__(message)
        self.step = step
        self.message = message
