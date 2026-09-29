class CaseNotFoundError(Exception):
    pass


class CaseAccessDeniedError(Exception):
    pass


class CaseConflictError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class CaseValidationError(Exception):
    def __init__(self, detail: str, context: dict[str, object] | None = None) -> None:
        self.detail = detail
        self.context = context
        super().__init__(detail)
