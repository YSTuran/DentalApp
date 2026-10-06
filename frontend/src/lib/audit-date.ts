function localDateToIso(value: string, addDays: number): string | undefined {
  if (!value) return undefined;
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day + addDays).toISOString();
}

export function auditDateBoundaries(dateFrom: string, dateTo: string) {
  return {
    createdFrom: localDateToIso(dateFrom, 0),
    createdBefore: localDateToIso(dateTo, 1),
  };
}
