import type { RoleCode } from "../types/auth";
import type {
  ManagedUser,
  ManagedUserListResponse,
  UserCreatedResponse,
  UserCreateInput,
} from "../types/user-management";
import { ApiError, apiRequest, csrfRequest } from "./api";

interface UserListFilters {
  search?: string;
  isActive?: boolean;
  role?: RoleCode;
  clinicId?: string;
  limit?: number;
  offset?: number;
}

function jsonBody(value: unknown): Pick<RequestInit, "headers" | "body"> {
  return {
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(value),
  };
}

export function listUsers(filters: UserListFilters): Promise<ManagedUserListResponse> {
  const query = new URLSearchParams();
  if (filters.search) query.set("search", filters.search);
  if (filters.isActive !== undefined) query.set("is_active", String(filters.isActive));
  if (filters.role) query.set("role", filters.role);
  if (filters.clinicId) query.set("clinic_id", filters.clinicId);
  query.set("limit", String(filters.limit ?? 20));
  query.set("offset", String(filters.offset ?? 0));
  return apiRequest<ManagedUserListResponse>(`/api/users?${query.toString()}`);
}

export function createUser(input: UserCreateInput): Promise<UserCreatedResponse> {
  const isGlobalRole = input.role === "system_admin" || input.role === "technician";
  return csrfRequest<UserCreatedResponse>("/api/users", {
    method: "POST",
    ...jsonBody({
      email: input.email,
      full_name: input.full_name,
      role: input.role,
      clinic_id: isGlobalRole ? null : input.clinic_id,
      reason: input.reason || null,
    }),
  });
}

export function changeUserStatus(
  userId: string,
  activate: boolean,
  reason: string,
): Promise<ManagedUser> {
  const action = activate ? "reactivate" : "deactivate";
  return csrfRequest<ManagedUser>(`/api/users/${userId}/${action}`, {
    method: "POST",
    ...jsonBody({ reason }),
  });
}

export function userErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const messages: Record<string, string> = {
      user_email_exists: "Bu e-posta adresiyle kayıtlı bir kullanıcı zaten var.",
      clinic_role_requires_clinic: "Bu rol için bir klinik seçmelisiniz.",
      global_role_cannot_have_clinic: "Bu rol herhangi bir kliniğe bağlanamaz.",
      system_admin_assignment_not_allowed:
        "Sistem yöneticisi rolü kullanıcı yönetimi ekranından atanamaz.",
      clinic_not_found: "Seçilen klinik bulunamadı.",
      clinic_inactive: "Pasif bir kliniğe kullanıcı atanamaz.",
      user_not_found: "Kullanıcı bulunamadı.",
      user_already_active: "Kullanıcı zaten aktif durumda.",
      user_already_inactive: "Kullanıcı zaten pasif durumda.",
      cannot_deactivate_self: "Oturum açtığınız hesabı pasifleştiremezsiniz.",
      last_system_admin: "Sistemde en az bir aktif sistem yöneticisi kalmalıdır.",
      firebase_service_unavailable: "Firebase hizmetine ulaşılamadı. Tekrar deneyin.",
      firebase_identity_missing: "Kullanıcının Firebase hesabı bulunamadı.",
      insufficient_permissions: "Bu işlem için yetkiniz bulunmuyor.",
      csrf_validation_failed: "Güvenlik doğrulaması başarısız oldu. Tekrar deneyin.",
    };
    return messages[error.detail] ?? "Kullanıcı işlemi tamamlanamadı.";
  }
  return error instanceof TypeError
    ? "FastAPI sunucusuna ulaşılamıyor."
    : "Beklenmeyen bir hata oluştu.";
}
