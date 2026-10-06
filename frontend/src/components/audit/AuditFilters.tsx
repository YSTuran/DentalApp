import { AUDIT_ACTION_LABELS, AUDIT_ENTITY_LABELS } from "../../lib/audit-labels";
import { EMPTY_AUDIT_FILTERS, type AuditFilterValues } from "../../lib/audit-filter-values";
import type { Clinic } from "../../types/clinic";

interface Props {
  clinics: Clinic[];
  value: AuditFilterValues;
  onChange: (value: AuditFilterValues) => void;
}

export function AuditFilters({ clinics, value, onChange }: Props) {
  const update = (changes: Partial<AuditFilterValues>) => onChange({ ...value, ...changes });
  const hasFilters = Object.values(value).some(Boolean);

  return (
    <div className="audit-filters">
      <label>İşlem
        <select value={value.action} onChange={(event) => update({ action: event.target.value })}>
          <option value="">Tüm işlemler</option>
          {Object.entries(AUDIT_ACTION_LABELS).map(([action, label]) => (
            <option key={action} value={action}>{label}</option>
          ))}
        </select>
      </label>
      <label>Kayıt türü
        <select value={value.entityType} onChange={(event) => update({ entityType: event.target.value })}>
          <option value="">Tümü</option>
          {Object.entries(AUDIT_ENTITY_LABELS).map(([type, label]) => <option key={type} value={type}>{label}</option>)}
        </select>
      </label>
      <label>Klinik
        <select value={value.clinicId} onChange={(event) => update({ clinicId: event.target.value })}>
          <option value="">Tümü</option>
          {clinics.map((clinic) => <option key={clinic.id} value={clinic.id}>{clinic.name}</option>)}
        </select>
      </label>
      <label>Başlangıç tarihi
        <input type="date" max={value.dateTo || undefined} value={value.dateFrom} onChange={(event) => update({ dateFrom: event.target.value })} />
      </label>
      <label>Bitiş tarihi
        <input type="date" min={value.dateFrom || undefined} value={value.dateTo} onChange={(event) => update({ dateTo: event.target.value })} />
      </label>
      <label>Kayıt ID
        <input value={value.entityId} onChange={(event) => update({ entityId: event.target.value })} placeholder="Tam kayıt kimliği" />
      </label>
      <div className="audit-filter-actions">
        <span>Filtreler otomatik uygulanır.</span>
        <button type="button" className="secondary-button" disabled={!hasFilters} onClick={() => onChange(EMPTY_AUDIT_FILTERS)}>Temizle</button>
      </div>
    </div>
  );
}
