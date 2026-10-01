export interface DynamicFieldRow {
  id: string;
  key: string;
  value: string;
}

interface Props {
  fields: DynamicFieldRow[];
  onChange: (fields: DynamicFieldRow[]) => void;
  disabled?: boolean;
}

export function DynamicFieldsEditor({ fields, onChange, disabled = false }: Props) {
  function update(id: string, field: "key" | "value", value: string) {
    onChange(fields.map((row) => row.id === id ? { ...row, [field]: value } : row));
  }

  return (
    <fieldset className="dynamic-fields" disabled={disabled}>
      <legend>Ek alanlar <span>(isteğe bağlı)</span></legend>
      {fields.map((row) => (
        <div className="dynamic-field-row" key={row.id}>
          <input
            aria-label="Ek alan adı"
            placeholder="Alan adı"
            value={row.key}
            onChange={(event) => update(row.id, "key", event.target.value)}
          />
          <input
            aria-label="Ek alan değeri"
            placeholder="Değer"
            value={row.value}
            onChange={(event) => update(row.id, "value", event.target.value)}
          />
          <button
            className="icon-button"
            type="button"
            aria-label="Ek alanı kaldır"
            onClick={() => onChange(fields.filter((item) => item.id !== row.id))}
          >×</button>
        </div>
      ))}
      <button
        className="secondary-button compact-button"
        type="button"
        onClick={() => onChange([...fields, { id: crypto.randomUUID(), key: "", value: "" }])}
      >Alan ekle</button>
    </fieldset>
  );
}

