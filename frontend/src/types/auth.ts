import type { ThemePreferences } from "./theme";

export type RoleCode =
  | "system_admin"
  | "clinic_manager"
  | "managing_dentist"
  | "dentist"
  | "clinic_staff"
  | "technician";

export interface ClinicRole {
  clinic_id: string;
  clinic_name?: string;
  role: RoleCode;
}

export interface CurrentUser {
  id: string;
  email: string;
  full_name: string;
  global_roles: RoleCode[];
  clinic_roles: ClinicRole[];
  preferences: ThemePreferences;
}
