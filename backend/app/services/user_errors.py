class UserNotFoundError(Exception):
    pass


class RoleAssignmentNotFoundError(Exception):
    pass


class ClinicAssignmentNotFoundError(Exception):
    pass


class UserAccessDeniedError(Exception):
    pass


class UserConflictError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class UserValidationError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class FirebaseSyncError(Exception):
    def __init__(self, detail: str = "firebase_service_unavailable") -> None:
        self.detail = detail
        super().__init__(detail)
