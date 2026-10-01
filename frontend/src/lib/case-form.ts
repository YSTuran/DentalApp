import type { DynamicFieldRow } from "../components/cases/DynamicFieldsEditor";

export function fieldsToObject(fields: DynamicFieldRow[]): Record<string, string> {
  return Object.fromEntries(
    fields
      .map((field) => [field.key.trim(), field.value.trim()])
      .filter(([key]) => key.length > 0),
  );
}
