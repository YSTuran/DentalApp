import type { AuditEventListResponse } from "../types/audit";
import { ApiError, apiRequest } from "./api";

export interface AuditFilters {
  action?: string;
  entityType?: string;
  entityId?: string;
  clinicId?: string;
  limit?: number;
  offset?: number;
}

export function listAuditEvents(filters: AuditFilters): Promise<AuditEventListResponse> {
  const query = new URLSearchParams();
  if (filters.action) query.set("action", filters.action);
  if (filters.entityType) query.set("entity_type", filters.entityType);
  if (filters.entityId) query.set("entity_id", filters.entityId);
  if (filters.clinicId) query.set("clinic_id", filters.clinicId);
  query.set("limit", String(filters.limit ?? 20));
  query.set("offset", String(filters.offset ?? 0));
  return apiRequest<AuditEventListResponse>(`/api/audit-events?${query.toString()}`);
}

export function auditErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.detail === "insufficient_permissions") {
      return "Audit kayıtlarını yalnızca sistem yöneticisi görüntüleyebilir.";
    }
    return "Audit kayıtları alınamadı.";
  }
  return error instanceof TypeError
    ? "FastAPI sunucusuna ulaşılamıyor."
    : "Beklenmeyen bir hata oluştu.";
}
