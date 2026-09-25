import { type FormEvent, useCallback, useEffect, useState } from "react";

import { DemoBanner } from "../components/DemoBanner";
import { ManagementHeader } from "../components/ManagementHeader";
import {
  changeClinicStatus,
  clinicErrorMessage,
  createClinic,
  listClinics,
  updateClinic,
} from "../lib/clinics-api";
import type { Clinic, ClinicFormInput } from "../types/clinic";

const PAGE_SIZE = 10;
const EMPTY_FORM: ClinicFormInput = {
  code: "",
  name: "",
  address: "",
  phone: "",
  reason: "",
};

type StatusFilter = "all" | "active" | "inactive";
type FormMode = { kind: "create" } | { kind: "edit"; clinic: Clinic };

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function ClinicsPage() {
  const [clinics, setClinics] = useState<Clinic[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("active");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [formMode, setFormMode] = useState<FormMode | null>(null);
  const [form, setForm] = useState<ClinicFormInput>(EMPTY_FORM);
  const [statusTarget, setStatusTarget] = useState<Clinic | null>(null);
  const [statusReason, setStatusReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const loadClinics = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listClinics({
        search,
        isActive:
          statusFilter === "all" ? undefined : statusFilter === "active",
        limit: PAGE_SIZE,
        offset,
      });
      setClinics(result.items);
      setTotal(result.total);
    } catch (loadError) {
      setError(clinicErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, [offset, search, statusFilter]);

  useEffect(() => {
    // Fetching remote data is the synchronization performed by this effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadClinics();
  }, [loadClinics]);

  function applySearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setOffset(0);
    setSearch(searchInput.trim());
  }

  function openCreateForm() {
    setFormMode({ kind: "create" });
    setForm(EMPTY_FORM);
    setError(null);
  }

  function openEditForm(clinic: Clinic) {
    setFormMode({ kind: "edit", clinic });
    setForm({
      code: clinic.code,
      name: clinic.name,
      address: clinic.address ?? "",
      phone: clinic.phone ?? "",
      reason: "",
    });
    setError(null);
  }

  async function submitClinicForm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (formMode === null) return;
    setSubmitting(true);
    setError(null);
    try {
      if (formMode.kind === "create") {
        await createClinic(form);
        setNotice("Klinik başarıyla oluşturuldu.");
      } else {
        await updateClinic(formMode.clinic.id, form);
        setNotice("Klinik bilgileri güncellendi.");
      }
      setFormMode(null);
      await loadClinics();
    } catch (submitError) {
      setError(clinicErrorMessage(submitError));
    } finally {
      setSubmitting(false);
    }
  }

  async function submitStatusChange(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (statusTarget === null) return;
    setSubmitting(true);
    setError(null);
    try {
      await changeClinicStatus(statusTarget.id, !statusTarget.is_active, statusReason);
      setNotice(
        statusTarget.is_active
          ? "Klinik pasife alındı."
          : "Klinik yeniden etkinleştirildi.",
      );
      setStatusTarget(null);
      setStatusReason("");
      await loadClinics();
    } catch (statusError) {
      setError(clinicErrorMessage(statusError));
    } finally {
      setSubmitting(false);
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
            <p className="eyebrow">SİSTEM YÖNETİMİ</p>
            <h1>Klinikler</h1>
            <p>Şubeleri oluşturun, bilgilerini güncelleyin ve durumlarını yönetin.</p>
          </div>
          <button className="primary-button compact-button" onClick={openCreateForm}>
            + Yeni klinik
          </button>
        </div>

        {notice !== null && <div className="success-message" role="status">{notice}</div>}
        {error !== null && <div className="form-error" role="alert">{error}</div>}

        <section className="management-card">
          <div className="filters-row">
            <form className="search-form" onSubmit={applySearch}>
              <label className="sr-only" htmlFor="clinic-search">Klinik ara</label>
              <input
                id="clinic-search"
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
                placeholder="Kod veya klinik adı"
              />
              <button className="secondary-button" type="submit">Ara</button>
            </form>
            <label className="filter-select">
              <span>Durum</span>
              <select
                value={statusFilter}
                onChange={(event) => {
                  setStatusFilter(event.target.value as StatusFilter);
                  setOffset(0);
                }}
              >
                <option value="active">Aktif</option>
                <option value="inactive">Pasif</option>
                <option value="all">Tümü</option>
              </select>
            </label>
          </div>

          {loading ? (
            <div className="table-state">Klinikler yükleniyor…</div>
          ) : clinics.length === 0 ? (
            <div className="table-state">Bu filtrelerle eşleşen klinik bulunamadı.</div>
          ) : (
            <div className="table-scroll">
              <table className="data-table">
                <thead><tr><th>Kod</th><th>Klinik</th><th>İletişim</th><th>Durum</th><th>Güncelleme</th><th /></tr></thead>
                <tbody>
                  {clinics.map((clinic) => (
                    <tr key={clinic.id}>
                      <td><span className="code-chip">{clinic.code}</span></td>
                      <td><strong>{clinic.name}</strong><small>{clinic.address || "Adres girilmedi"}</small></td>
                      <td>{clinic.phone || "—"}</td>
                      <td><span className={`state-chip ${clinic.is_active ? "active" : "inactive"}`}>{clinic.is_active ? "Aktif" : "Pasif"}</span></td>
                      <td><small>{formatDate(clinic.updated_at)}</small></td>
                      <td>
                        <div className="row-actions">
                          <button onClick={() => openEditForm(clinic)}>Düzenle</button>
                          <button className={clinic.is_active ? "danger-action" : "success-action"} onClick={() => { setStatusTarget(clinic); setStatusReason(""); }}>
                            {clinic.is_active ? "Pasife al" : "Etkinleştir"}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
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

      {formMode !== null && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal-card" role="dialog" aria-modal="true" aria-labelledby="clinic-form-title">
            <div className="modal-heading">
              <div><p className="eyebrow">KLİNİK</p><h2 id="clinic-form-title">{formMode.kind === "create" ? "Yeni klinik" : "Kliniği düzenle"}</h2></div>
              <button className="icon-button" onClick={() => setFormMode(null)} aria-label="Pencereyi kapat">×</button>
            </div>
            <form className="management-form" onSubmit={submitClinicForm}>
              <label>Klinik kodu<input value={form.code} onChange={(event) => setForm({ ...form, code: event.target.value })} maxLength={50} required /></label>
              <label>Klinik adı<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} maxLength={200} required /></label>
              <label>Adres<textarea value={form.address} onChange={(event) => setForm({ ...form, address: event.target.value })} rows={3} /></label>
              <label>Telefon<input value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} maxLength={32} /></label>
              <label>Değişiklik gerekçesi <span className="optional-label">İsteğe bağlı</span><textarea value={form.reason} onChange={(event) => setForm({ ...form, reason: event.target.value })} rows={2} maxLength={2000} /></label>
              <div className="modal-actions"><button type="button" className="secondary-button" onClick={() => setFormMode(null)}>Vazgeç</button><button className="primary-button compact-button" disabled={submitting}>{submitting ? "Kaydediliyor…" : "Kaydet"}</button></div>
            </form>
          </section>
        </div>
      )}

      {statusTarget !== null && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal-card modal-card-small" role="dialog" aria-modal="true" aria-labelledby="status-title">
            <div className="modal-heading"><div><p className="eyebrow">DURUM DEĞİŞİKLİĞİ</p><h2 id="status-title">{statusTarget.is_active ? "Kliniği pasife al" : "Kliniği etkinleştir"}</h2></div><button className="icon-button" onClick={() => setStatusTarget(null)} aria-label="Pencereyi kapat">×</button></div>
            <p><strong>{statusTarget.name}</strong> için bu işlem audit kaydına yazılacaktır.</p>
            <form className="management-form" onSubmit={submitStatusChange}>
              <label>Gerekçe<textarea value={statusReason} onChange={(event) => setStatusReason(event.target.value)} minLength={3} maxLength={2000} rows={3} required autoFocus /></label>
              <div className="modal-actions"><button type="button" className="secondary-button" onClick={() => setStatusTarget(null)}>Vazgeç</button><button className="primary-button compact-button" disabled={submitting}>{submitting ? "İşleniyor…" : "Onayla"}</button></div>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}
