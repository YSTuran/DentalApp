from enum import StrEnum


class RoleCode(StrEnum):
    SYSTEM_ADMIN = "system_admin"
    CLINIC_MANAGER = "clinic_manager"
    MANAGING_DENTIST = "managing_dentist"
    DENTIST = "dentist"
    CLINIC_STAFF = "clinic_staff"
    TECHNICIAN = "technician"

    @property
    def is_global(self) -> bool:
        return self in {self.SYSTEM_ADMIN, self.TECHNICIAN}
