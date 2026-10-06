export interface AuditFilterValues {
  action: string;
  entityType: string;
  entityId: string;
  clinicId: string;
  dateFrom: string;
  dateTo: string;
}

export const EMPTY_AUDIT_FILTERS: AuditFilterValues = {
  action: "",
  entityType: "",
  entityId: "",
  clinicId: "",
  dateFrom: "",
  dateTo: "",
};
