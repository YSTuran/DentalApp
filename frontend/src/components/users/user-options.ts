import type { RoleCode } from "../../types/auth";
import type { ClinicAssignment, UserCreateInput } from "../../types/user-management";

export const PAGE_SIZE = 10;
export const GLOBAL_ROLES = new Set<RoleCode>(["technician"]);
export const ROLE_LABELS: Record<RoleCode, string> = {
  system_admin: "Sistem yöneticisi",
  dentist: "Hekim",
  managing_dentist: "Yönetici hekim",
  clinic_staff: "Klinik personeli / asistan",
  clinic_manager: "Klinik yöneticisi",
  technician: "Laboratuvar teknisyeni",
};
export const ASSIGNABLE_ROLE_OPTIONS: Array<{ value: RoleCode; label: string }> = [
  { value: "dentist", label: "Hekim" },
  { value: "managing_dentist", label: "Yönetici hekim" },
  { value: "clinic_staff", label: "Klinik personeli / asistan" },
  { value: "clinic_manager", label: "Klinik yöneticisi" },
  { value: "technician", label: "Laboratuvar teknisyeni" },
];
export const FILTER_ROLE_OPTIONS: Array<{ value: RoleCode; label: string }> = [
  ...ASSIGNABLE_ROLE_OPTIONS,
  { value: "system_admin", label: "Sistem yöneticisi" },
];
export const EMPTY_USER_FORM: UserCreateInput = {
  email: "",
  full_name: "",
  role: "dentist",
  clinic_id: "",
  reason: "",
};

export interface ClinicStatusTarget {
  userId: string;
  assignment: ClinicAssignment;
}
