import type { CaseReport } from "../types/report";
import { apiRequest } from "./api";

export interface ReportFilters {
  dateFrom?: string;
  dateTo?: string;
  clinicId?: string;
}

export function getCaseReport(filters: ReportFilters, signal?: AbortSignal): Promise<CaseReport> {
  const query = new URLSearchParams();
  if (filters.dateFrom) query.set("date_from", filters.dateFrom);
  if (filters.dateTo) query.set("date_to", filters.dateTo);
  if (filters.clinicId) query.set("clinic_id", filters.clinicId);
  const suffix = query.size > 0 ? `?${query.toString()}` : "";
  return apiRequest(`/api/reports/cases${suffix}`, { signal });
}
