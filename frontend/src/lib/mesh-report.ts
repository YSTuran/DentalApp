export function meshReportItems(
  report: Record<string, unknown> | null,
  key: "issues" | "warnings",
): string[] {
  const value = report?.[key];
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

export function hasMeshWarnings(report: Record<string, unknown> | null): boolean {
  return meshReportItems(report, "warnings").length > 0;
}
