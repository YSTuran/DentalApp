import type { Clinic, ClinicFormInput, ClinicListResponse } from "../types/clinic";
import { ApiError, apiRequest, csrfRequest } from "./api";

interface ClinicListFilters {
  search?: string;
  isActive?: boolean;
  limit?: number;
  offset?: number;
}

function jsonBody(value: unknown): Pick<RequestInit, "headers" | "body"> {
  return {
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(value),
  };
}

export function listClinics(filters: ClinicListFilters): Promise<ClinicListResponse> {
  const query = new URLSearchParams();
  if (filters.search) query.set("search", filters.search);
  if (filters.isActive !== undefined) query.set("is_active", String(filters.isActive));
  query.set("limit", String(filters.limit ?? 20));
  query.set("offset", String(filters.offset ?? 0));
  return apiRequest<ClinicListResponse>(`/api/clinics?${query.toString()}`);
}

export function createClinic(input: ClinicFormInput): Promise<Clinic> {
  return csrfRequest<Clinic>("/api/clinics", {
    method: "POST",
    ...jsonBody({
      code: input.code,
      name: input.name,
      address: input.address || null,
      phone: input.phone || null,
      reason: input.reason || null,
    }),
  });
}

export function updateClinic(clinicId: string, input: ClinicFormInput): Promise<Clinic> {
  return csrfRequest<Clinic>(`/api/clinics/${clinicId}`, {
    method: "PATCH",
    ...jsonBody({
      code: input.code,
      name: input.name,
      address: input.address || null,
      phone: input.phone || null,
      reason: input.reason || null,
    }),
  });
}

export function changeClinicStatus(
  clinicId: string,
  activate: boolean,
  reason: string,
): Promise<Clinic> {
  const action = activate ? "reactivate" : "deactivate";
  return csrfRequest<Clinic>(`/api/clinics/${clinicId}/${action}`, {
    method: "POST",
    ...jsonBody({ reason }),
  });
}

export function clinicErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const messages: Record<string, string> = {
      clinic_code_exists: "Bu klinik kodu zaten kullanılıyor.",
      clinic_no_changes: "Klinik bilgilerinde kaydedilecek bir değişiklik yok.",
      clinic_already_active: "Klinik zaten aktif durumda.",
      clinic_already_inactive: "Klinik zaten pasif durumda.",
      clinic_not_found: "Klinik bulunamadı.",
      insufficient_permissions: "Bu işlem için yetkiniz bulunmuyor.",
      csrf_validation_failed: "Güvenlik doğrulaması başarısız oldu. Tekrar deneyin.",
    };
    return messages[error.detail] ?? "Klinik işlemi tamamlanamadı.";
  }
  return error instanceof TypeError
    ? "FastAPI sunucusuna ulaşılamıyor."
    : "Beklenmeyen bir hata oluştu.";
}
