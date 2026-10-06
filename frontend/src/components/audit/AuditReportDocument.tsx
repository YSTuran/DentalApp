import { auditToneFor } from "../../lib/audit-colors";
import type { AuditFilterValues } from "../../lib/audit-filter-values";
import { formatAuditReason } from "../../lib/audit-format";
import { AUDIT_ACTION_LABELS, AUDIT_ENTITY_LABELS } from "../../lib/audit-labels";
import type { AuditEvent } from "../../types/audit";
import "./audit-report.css";

interface Props {
  events: AuditEvent[];
  filters: AuditFilterValues;
  clinicNames: Map<string, string>;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(new Date(value));
}

function filterLabels(filters: AuditFilterValues, clinicNames: Map<string, string>): string[] {
  const labels: string[] = [];
  if (filters.action) labels.push(`İşlem: ${AUDIT_ACTION_LABELS[filters.action] ?? filters.action}`);
  if (filters.entityType) labels.push(`Kayıt: ${AUDIT_ENTITY_LABELS[filters.entityType] ?? filters.entityType}`);
  if (filters.clinicId) labels.push(`Klinik: ${clinicNames.get(filters.clinicId) ?? filters.clinicId}`);
  if (filters.entityId) labels.push(`Kayıt ID: ${filters.entityId}`);
  if (filters.dateFrom) labels.push(`Başlangıç: ${filters.dateFrom}`);
  if (filters.dateTo) labels.push(`Bitiş: ${filters.dateTo}`);
  return labels;
}

export function AuditReportDocument({ events, filters, clinicNames }: Props) {
  const activeFilters = filterLabels(filters, clinicNames);

  return (
    <article className="audit-report-document">
      <header className="audit-report-header">
        <div><span>DENTALAPP</span><h1>Audit kayıtları raporu</h1></div>
        <dl>
          <div><dt>Oluşturulma</dt><dd>{formatDate(new Date().toISOString())}</dd></div>
          <div><dt>Kayıt sayısı</dt><dd>{events.length}</dd></div>
        </dl>
      </header>

      <section className="audit-report-filters">
        <strong>Uygulanan filtreler</strong>
        <div>
          {activeFilters.length > 0
            ? activeFilters.map((label) => <span key={label}>{label}</span>)
            : <span>Tüm audit kayıtları</span>}
        </div>
      </section>

      <div className="audit-report-list">
        {events.map((event, index) => {
          const tone = auditToneFor(event.action, event.entity_type);
          return (
            <section className={`audit-report-card audit-tone-${tone}`} key={event.id}>
              <header>
                <div>
                  <span className="audit-report-index">#{index + 1}</span>
                  <strong>{AUDIT_ACTION_LABELS[event.action] ?? event.action}</strong>
                  <small>{event.action}</small>
                </div>
                <time dateTime={event.created_at}>{formatDate(event.created_at)}</time>
              </header>
              <dl>
                <div><dt>İşlemi yapan</dt><dd>{event.actor_email ?? "Sistem"}</dd></div>
                <div><dt>Kayıt türü</dt><dd>{AUDIT_ENTITY_LABELS[event.entity_type] ?? event.entity_type}</dd></div>
                <div><dt>Kayıt ID</dt><dd>{event.entity_id}</dd></div>
                <div><dt>Klinik</dt><dd>{event.clinic_id ? (clinicNames.get(event.clinic_id) ?? event.clinic_id) : "-"}</dd></div>
                <div><dt>IP adresi</dt><dd>{event.ip_address ?? "-"}</dd></div>
                <div className="audit-report-reason"><dt>Gerekçe</dt><dd>{formatAuditReason(event.reason)}</dd></div>
              </dl>
            </section>
          );
        })}
      </div>

      <footer>Bu rapor değiştirilemez audit kayıtlarının filtrelenmiş görünümünden oluşturulmuştur.</footer>
    </article>
  );
}
