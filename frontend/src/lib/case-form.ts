import type { DynamicFieldRow } from "../components/cases/DynamicFieldsEditor";

export function fieldsToObject(fields: DynamicFieldRow[]): Record<string, string> {
  return Object.fromEntries(
    fields
      .map((field) => [field.key.trim(), field.value.trim()])
      .filter(([key]) => key.length > 0),
  );
}

export function objectToFields(fields: Record<string, unknown>): DynamicFieldRow[] {
  return Object.entries(fields).map(([key, value], index) => ({
    id: `existing-${index}`,
    key,
    value: String(value),
  }));
}

export function parseToothNumbers(value: string): string[] {
  return value
    .split(/[\s,;]+/)
    .map((tooth) => tooth.trim())
    .filter(Boolean);
}
