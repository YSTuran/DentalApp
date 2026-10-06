import type { AuditEvent, AuditEventListResponse } from "../types/audit";
import { ApiError, apiRequest } from "./api";

export interface AuditFilters {
  action?: string;
  entityType?: string;
  entityId?: string;
  clinicId?: string;
  createdFrom?: string;
  createdBefore?: string;
  limit?: number;
  offset?: number;
}

export function listAuditEvents(
  filters: AuditFilters,
  signal?: AbortSignal,
): Promise<AuditEventListResponse> {
  const query = new URLSearchParams();
  if (filters.action) query.set("action", filters.action);
  if (filters.entityType) query.set("entity_type", filters.entityType);
  if (filters.entityId) query.set("entity_id", filters.entityId);
  if (filters.clinicId) query.set("clinic_id", filters.clinicId);
  if (filters.createdFrom) query.set("created_from", filters.createdFrom);
  if (filters.createdBefore) query.set("created_before", filters.createdBefore);
  query.set("limit", String(filters.limit ?? 20));
  query.set("offset", String(filters.offset ?? 0));
  return apiRequest<AuditEventListResponse>(`/api/audit-events?${query.toString()}`, { signal });
}

export async function listAllAuditEvents(
  filters: AuditFilters,
  signal?: AbortSignal,
): Promise<AuditEvent[]> {
  const activeFilters = { ...filters };
  delete activeFilters.limit;
  delete activeFilters.offset;
  const items: AuditEvent[] = [];
  let offset = 0;
  let total = 1;

  while (offset < total) {
    const page = await listAuditEvents(
      { ...activeFilters, limit: 100, offset },
      signal,
    );
    items.push(...page.items);
    total = page.total;
    offset += page.items.length;
    if (page.items.length === 0) break;
  }
  return items;
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
