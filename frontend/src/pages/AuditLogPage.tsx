import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { DemoBanner } from "../components/DemoBanner";
import { ManagementHeader } from "../components/ManagementHeader";
import { AUDIT_LEGEND, auditToneFor } from "../lib/audit-colors";
import { formatAuditReason } from "../lib/audit-format";
import { type AuditFilters, auditErrorMessage, listAuditEvents } from "../lib/audit-api";
import { listClinics } from "../lib/clinics-api";
import type { AuditEvent } from "../types/audit";
import type { Clinic } from "../types/clinic";

const PAGE_SIZE = 15;
const EMPTY_FILTERS = {
  action: "",
  entityType: "",
  entityId: "",
  clinicId: "",
};

const ACTION_LABELS: Record<string, string> = {
  "auth.session_created": "Oturum açıldı",
  "auth.session_ended": "Oturum kapatıldı",
  "account.password_changed": "Parola değiştirildi",
  "clinic.created": "Klinik oluşturuldu",
  "clinic.updated": "Klinik güncellendi",
  "clinic.deactivated": "Klinik pasifleştirildi",
  "clinic.reactivated": "Klinik etkinleştirildi",
  "user.created": "Kullanıcı oluşturuldu",
  "user.updated": "Kullanıcı güncellendi",
  "user.deactivated": "Kullanıcı pasifleştirildi",
  "user.reactivated": "Kullanıcı etkinleştirildi",
  "user.role_assigned": "Rol atandı",
  "user.role_changed": "Rol veya klinik değiştirildi",
  "user.role_deactivated": "Rol pasifleştirildi",
  "user.role_reactivated": "Rol etkinleştirildi",
  "case.created": "Vaka oluşturuldu",
  "case.updated": "Vaka bilgileri güncellendi",
  "case.submitted": "Vaka yönetici onayına gönderildi",
  "case.cancelled": "Vaka iptal edildi",
  "case.manager_approved": "Tarama yönetici tarafından onaylandı",
  "case.manager_revision_requested": "Tarama düzeltmesi istendi",
  "case.manager_rejected": "Vaka kesin reddedildi",
  "case.design_submitted": "Tasarım hekim onayına gönderildi",
  "case.design_approved": "Tasarım hekim tarafından onaylandı",
  "case.design_revision_requested": "Tasarım düzeltmesi istendi",
  "case.file_upload_started": "Dosya yüklemesi başlatıldı",
  "case.file_uploaded": "Dosya yüklendi",
  "case.file_upload_failed": "Dosya yüklemesi başarısız oldu",
  "case.file_upload_expired": "Dosya yükleme süresi doldu",
  "case.file_downloaded": "Dosya indirildi",
  "case.file_previewed": "Dosya önizlendi",
};

const ENTITY_LABELS: Record<string, string> = {
  clinic: "Klinik",
  user: "Kullanıcı",
  user_role_assignment: "Rol ataması",
  case: "Vaka",
  case_file_version: "Vaka dosyası",
  case_upload_session: "Dosya yüklemesi",
};

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
  const [filterForm, setFilterForm] = useState(EMPTY_FILTERS);
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const clinicNames = useMemo(
    () => new Map(clinics.map((clinic) => [clinic.id, clinic.name])),
    [clinics],
  );

  const loadEvents = useCallback(async () => {
    setLoading(true);
    setError(null);
    const query: AuditFilters = {
      action: filters.action || undefined,
      entityType: filters.entityType || undefined,
      entityId: filters.entityId || undefined,
      clinicId: filters.clinicId || undefined,
      limit: PAGE_SIZE,
      offset,
    };
    try {
      const result = await listAuditEvents(query);
      setEvents(result.items);
      setTotal(result.total);
    } catch (loadError) {
      setError(auditErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, [filters, offset]);

  useEffect(() => {
    // Remote list synchronization is intentionally performed in this effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadEvents();
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

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setOffset(0);
    setFilters({
      action: filterForm.action.trim(),
      entityType: filterForm.entityType.trim(),
      entityId: filterForm.entityId.trim(),
      clinicId: filterForm.clinicId,
    });
  }

  function clearFilters() {
    setFilterForm(EMPTY_FILTERS);
    setFilters(EMPTY_FILTERS);
    setOffset(0);
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
          <span className="immutable-badge">Değiştirilemez kayıt</span>
        </div>

        {error !== null && <div className="form-error" role="alert">{error}</div>}

        <section className="management-card">
          <form className="audit-filters" onSubmit={applyFilters}>
            <label>İşlem
              <input list="audit-actions" value={filterForm.action} onChange={(event) => setFilterForm({ ...filterForm, action: event.target.value })} placeholder="Örn. user.created" />
              <datalist id="audit-actions">
                {Object.entries(ACTION_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </datalist>
            </label>
            <label>Kayıt türü
              <select value={filterForm.entityType} onChange={(event) => setFilterForm({ ...filterForm, entityType: event.target.value })}>
                <option value="">Tümü</option>
                <option value="user">Kullanıcı</option>
                <option value="user_role_assignment">Rol ataması</option>
                <option value="clinic">Klinik</option>
              </select>
            </label>
            <label>Klinik
              <select value={filterForm.clinicId} onChange={(event) => setFilterForm({ ...filterForm, clinicId: event.target.value })}>
                <option value="">Tümü</option>
                {clinics.map((clinic) => <option key={clinic.id} value={clinic.id}>{clinic.name}</option>)}
              </select>
            </label>
            <label>Kayıt ID
              <input value={filterForm.entityId} onChange={(event) => setFilterForm({ ...filterForm, entityId: event.target.value })} placeholder="Tam kayıt kimliği" />
            </label>
            <div className="audit-filter-actions">
              <button type="button" className="secondary-button" onClick={clearFilters}>Temizle</button>
              <button className="primary-button compact-button">Filtrele</button>
            </div>
          </form>

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
                      <td><span className={`action-chip audit-tone-${tone}`}>{ACTION_LABELS[auditEvent.action] ?? auditEvent.action}</span><small>{auditEvent.action}</small></td>
                      <td>{auditEvent.actor_email ?? "Sistem"}</td>
                      <td><strong>{ENTITY_LABELS[auditEvent.entity_type] ?? auditEvent.entity_type}</strong><small className="audit-entity-id">{auditEvent.entity_id}</small></td>
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
              <div><p className="eyebrow">AUDIT DETAYI</p><h2 id="audit-detail-title">{ACTION_LABELS[selectedEvent.action] ?? selectedEvent.action}</h2></div>
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
    </div>
  );
}
