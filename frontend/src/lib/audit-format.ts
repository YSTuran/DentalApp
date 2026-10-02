export function formatAuditReason(reason: string | null | undefined): string {
  const normalizedReason = reason?.trim();
  return normalizedReason ? normalizedReason : "-";
}
