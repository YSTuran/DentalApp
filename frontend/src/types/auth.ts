export type RoleCode =
  | "system_admin"
  | "clinic_manager"
  | "managing_dentist"
  | "dentist"
  | "clinic_staff"
  | "technician";

export interface ClinicRole {
  clinic_id: string;
  role: RoleCode;
}

export interface CurrentUser {
  id: string;
  email: string;
  full_name: string;
  global_roles: RoleCode[];
  clinic_roles: ClinicRole[];
}
