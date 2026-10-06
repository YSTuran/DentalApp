import { useCallback, useEffect, useMemo, useState } from "react";

import { DemoBanner } from "../components/DemoBanner";
import { ManagementHeader } from "../components/ManagementHeader";
import { AuditFilters } from "../components/audit/AuditFilters";
import { AuditReportDocument } from "../components/audit/AuditReportDocument";
import { PrintPortal } from "../components/printing/PrintPortal";
import { AUDIT_LEGEND, auditToneFor } from "../lib/audit-colors";
import { auditDateBoundaries } from "../lib/audit-date";
import { EMPTY_AUDIT_FILTERS, type AuditFilterValues } from "../lib/audit-filter-values";
import { formatAuditReason } from "../lib/audit-format";
import { type AuditFilters as AuditQueryFilters, auditErrorMessage, listAllAuditEvents, listAuditEvents } from "../lib/audit-api";
import { AUDIT_ACTION_LABELS, AUDIT_ENTITY_LABELS } from "../lib/audit-labels";
import { listClinics } from "../lib/clinics-api";
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import { usePrintDocument } from "../hooks/usePrintDocument";
import type { AuditEvent } from "../types/audit";
import type { Clinic } from "../types/clinic";

const PAGE_SIZE = 15;

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(new Date(value));
}

function jsonText(value: Record<string, unknown> | null): string {
  return value === null ? "Kayıt yok" : JSON.stringify(value, null, 2);
}

export function AuditLogPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [clinics, setClinics] = useState<Clinic[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [filterValues, setFilterValues] = useState<AuditFilterValues>(EMPTY_AUDIT_FILTERS);
  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [printEvents, setPrintEvents] = useState<AuditEvent[]>([]);
  const { isPrinting, print } = usePrintDocument();

  const clinicNames = useMemo(
    () => new Map(clinics.map((clinic) => [clinic.id, clinic.name])),
    [clinics],
  );

  const debouncedEntityId = useDebouncedValue(filterValues.entityId.trim(), 400);
  const queryFilters = useMemo<AuditQueryFilters>(() => ({
    action: filterValues.action || undefined,
    entityType: filterValues.entityType || undefined,
    entityId: debouncedEntityId || undefined,
    clinicId: filterValues.clinicId || undefined,
    ...auditDateBoundaries(filterValues.dateFrom, filterValues.dateTo),
    limit: PAGE_SIZE,
    offset,
  }), [
    debouncedEntityId,
    filterValues.action,
    filterValues.clinicId,
    filterValues.dateFrom,
    filterValues.dateTo,
    filterValues.entityType,
    offset,
  ]);

  const loadEvents = useCallback(async (signal: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const result = await listAuditEvents(queryFilters, signal);
      setEvents(result.items);
      setTotal(result.total);
    } catch (loadError) {
      if (signal.aborted) return;
      setError(auditErrorMessage(loadError));
    } finally {
      if (!signal.aborted) setLoading(false);
    }
  }, [queryFilters]);

  useEffect(() => {
    const controller = new AbortController();
    // Remote list synchronization is intentionally performed in this effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadEvents(controller.signal);
    return () => controller.abort();
  }, [loadEvents]);

  useEffect(() => {
    let active = true;
    void listClinics({ limit: 100, offset: 0 })
      .then((result) => {
        if (active) setClinics(result.items);
      })
      .catch(() => {
        // The audit table can still be used when clinic labels cannot be loaded.
      });
    return () => {
      active = false;
    };
  }, []);

  function changeFilters(nextFilters: AuditFilterValues) {
    setFilterValues(nextFilters);
    setOffset(0);
  }

  async function printFilteredAuditEvents() {
    setExporting(true);
    setError(null);
    try {
      const allEvents = await listAllAuditEvents({
        ...queryFilters,
        entityId: filterValues.entityId.trim() || undefined,
      });
      setPrintEvents(allEvents);
      print();
    } catch (exportError) {
      setError(auditErrorMessage(exportError));
    } finally {
      setExporting(false);
    }
  }

  const pageStart = total === 0 ? 0 : offset + 1;
  const pageEnd = Math.min(offset + PAGE_SIZE, total);

  return (
    <div className="dashboard-shell">
      <DemoBanner />
      <ManagementHeader />
      <main className="management-content">
        <div className="page-heading">
          <div>
            <p className="eyebrow">DENETİM İZİ</p>
            <h1>Audit kayıtları</h1>
            <p>Kim, ne zaman, hangi kaydı ve hangi gerekçeyle değiştirdi görüntüleyin.</p>
          </div>
          <div className="audit-page-actions">
            <span className="immutable-badge">Değiştirilemez kayıt</span>
            <button
              className="secondary-button"
              type="button"
              disabled={loading || total === 0 || exporting}
              onClick={() => void printFilteredAuditEvents()}
            >
              {exporting ? "Rapor hazırlanıyor…" : "PDF olarak yazdır"}
            </button>
          </div>
        </div>

        {error !== null && <div className="form-error" role="alert">{error}</div>}

        <section className="management-card">
          <AuditFilters clinics={clinics} value={filterValues} onChange={changeFilters} />

          <div className="audit-legend" aria-label="Audit kayıt renkleri">
            <span className="audit-legend-title">Renk anahtarı</span>
            {AUDIT_LEGEND.map((item) => (
              <span className={`audit-legend-item audit-tone-${item.tone}`} key={item.tone}>
                <span aria-hidden="true" />{item.label}
              </span>
            ))}
          </div>

          {loading ? (
            <div className="table-state">Audit kayıtları yükleniyor…</div>
          ) : events.length === 0 ? (
            <div className="table-state">Bu filtrelerle eşleşen audit kaydı bulunamadı.</div>
          ) : (
            <div className="table-scroll">
              <table className="data-table audit-table">
                <thead><tr><th>Zaman</th><th>İşlem</th><th>Kaydı yapan</th><th>Kayıt</th><th>Klinik</th><th>Gerekçe</th><th /></tr></thead>
                <tbody>
                  {events.map((auditEvent) => {
                    const tone = auditToneFor(auditEvent.action, auditEvent.entity_type);
                    return (
                    <tr className={`audit-row audit-tone-${tone}`} key={auditEvent.id}>
                      <td><strong>{formatDate(auditEvent.created_at)}</strong><small>{auditEvent.ip_address ?? "IP bilgisi yok"}</small></td>
                      <td><span className={`action-chip audit-tone-${tone}`}>{AUDIT_ACTION_LABELS[auditEvent.action] ?? auditEvent.action}</span><small>{auditEvent.action}</small></td>
                      <td>{auditEvent.actor_email ?? "Sistem"}</td>
                      <td><strong>{AUDIT_ENTITY_LABELS[auditEvent.entity_type] ?? auditEvent.entity_type}</strong><small className="audit-entity-id">{auditEvent.entity_id}</small></td>
                      <td>{auditEvent.clinic_id === null ? "—" : (clinicNames.get(auditEvent.clinic_id) ?? auditEvent.clinic_id)}</td>
                      <td><span className="reason-preview">{formatAuditReason(auditEvent.reason)}</span></td>
                      <td><div className="row-actions"><button onClick={() => setSelectedEvent(auditEvent)}>Detay</button></div></td>
                    </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          <div className="pagination-row">
            <span>{pageStart}–{pageEnd} / {total}</span>
            <div>
              <button className="secondary-button" disabled={offset === 0 || loading} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>Önceki</button>
              <button className="secondary-button" disabled={offset + PAGE_SIZE >= total || loading} onClick={() => setOffset(offset + PAGE_SIZE)}>Sonraki</button>
            </div>
          </div>
        </section>
      </main>

      {selectedEvent !== null && (
        <div className="modal-backdrop" role="presentation">
          <section className={`modal-card audit-detail-modal audit-tone-${auditToneFor(selectedEvent.action, selectedEvent.entity_type)}`} role="dialog" aria-modal="true" aria-labelledby="audit-detail-title">
            <div className="modal-heading">
              <div><p className="eyebrow">AUDIT DETAYI</p><h2 id="audit-detail-title">{AUDIT_ACTION_LABELS[selectedEvent.action] ?? selectedEvent.action}</h2></div>
              <button className="icon-button" onClick={() => setSelectedEvent(null)} aria-label="Pencereyi kapat">×</button>
            </div>
            <dl className="audit-metadata">
              <div><dt>Zaman</dt><dd>{formatDate(selectedEvent.created_at)}</dd></div>
              <div><dt>İşlem kodu</dt><dd>{selectedEvent.action}</dd></div>
              <div><dt>İşlemi yapan</dt><dd>{selectedEvent.actor_email ?? "Sistem"}</dd></div>
              <div><dt>Kayıt</dt><dd>{selectedEvent.entity_type} · {selectedEvent.entity_id}</dd></div>
              <div><dt>Klinik</dt><dd>{selectedEvent.clinic_id === null ? "—" : (clinicNames.get(selectedEvent.clinic_id) ?? selectedEvent.clinic_id)}</dd></div>
              <div><dt>Gerekçe</dt><dd>{formatAuditReason(selectedEvent.reason)}</dd></div>
              <div><dt>IP adresi</dt><dd>{selectedEvent.ip_address ?? "—"}</dd></div>
            </dl>
            <div className="audit-json-grid">
              <section><h3>Önceki değer</h3><pre>{jsonText(selectedEvent.before_data)}</pre></section>
              <section><h3>Sonraki değer</h3><pre>{jsonText(selectedEvent.after_data)}</pre></section>
              <section><h3>Bağlam</h3><pre>{jsonText(selectedEvent.context)}</pre></section>
            </div>
            <div className="modal-actions"><button className="primary-button compact-button" onClick={() => setSelectedEvent(null)}>Kapat</button></div>
          </section>
        </div>
      )}
      {isPrinting && (
        <PrintPortal>
          <AuditReportDocument
            events={printEvents}
            filters={filterValues}
            clinicNames={clinicNames}
          />
        </PrintPortal>
      )}
    </div>
  );
}
