"""TMS Elite integration exceptions."""


class TmsEliteError(Exception):
    """Base integration error."""


class TmsEliteConfigError(TmsEliteError):
    pass


class TmsEliteHttpError(TmsEliteError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class TmsEliteMappingError(TmsEliteError):
    pass
