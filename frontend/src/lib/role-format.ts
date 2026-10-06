import type { CurrentUser, RoleCode } from "../types/auth";

export const roleLabels: Record<RoleCode, string> = {
  system_admin: "Sistem yöneticisi",
  clinic_manager: "Klinik yöneticisi",
  managing_dentist: "Yönetici hekim",
  dentist: "Hekim",
  clinic_staff: "Klinik personeli / asistan",
  technician: "Laboratuvar teknisyeni",
};

export function userRoleLabels(user: CurrentUser): string[] {
  return [
    ...new Set([
      ...user.global_roles.map((role) => roleLabels[role]),
      ...user.clinic_roles.map(({ role }) => roleLabels[role]),
    ]),
  ];
}
