import type { RoleCode } from "./auth";

export interface RoleAssignment {
  id: string;
  role: RoleCode;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ClinicAssignment {
  id: string;
  clinic_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ManagedUser {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  role_assignments: RoleAssignment[];
  clinic_assignments: ClinicAssignment[];
}

export interface ManagedUserListResponse {
  items: ManagedUser[];
  total: number;
  limit: number;
  offset: number;
}

export interface UserCreateInput {
  email: string;
  full_name: string;
  role: RoleCode;
  clinic_id: string;
  reason: string;
}

export interface RoleAssignmentUpdateInput {
  role: RoleCode;
  reason: string;
}

export interface ClinicAssignmentCreateInput {
  clinic_id: string;
  reason: string;
}

export interface UserCreatedResponse {
  user: ManagedUser;
  temporary_password: string;
}
