import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { useAuth } from "../auth/AuthContext";
import { DemoBanner } from "../components/DemoBanner";
import { ManagementHeader } from "../components/ManagementHeader";
import { listClinics } from "../lib/clinics-api";
import {
  changeUserStatus,
  createUser,
  listUsers,
  userErrorMessage,
} from "../lib/users-api";
import type { RoleCode } from "../types/auth";
import type { Clinic } from "../types/clinic";
import type { ManagedUser, UserCreateInput } from "../types/user-management";

const PAGE_SIZE = 10;
const GLOBAL_ROLES = new Set<RoleCode>(["technician"]);
const ROLE_LABELS: Record<RoleCode, string> = {
  system_admin: "Sistem yöneticisi",
  dentist: "Hekim",
  managing_dentist: "Yönetici hekim",
  clinic_staff: "Klinik personeli / asistan",
  clinic_manager: "Klinik yöneticisi",
  technician: "Laboratuvar teknisyeni",
};
const ASSIGNABLE_ROLE_OPTIONS: Array<{ value: RoleCode; label: string }> = [
  { value: "dentist", label: "Hekim" },
  { value: "managing_dentist", label: "Yönetici hekim" },
  { value: "clinic_staff", label: "Klinik personeli / asistan" },
  { value: "clinic_manager", label: "Klinik yöneticisi" },
  { value: "technician", label: "Laboratuvar teknisyeni" },
];
const FILTER_ROLE_OPTIONS: Array<{ value: RoleCode; label: string }> = [
  ...ASSIGNABLE_ROLE_OPTIONS,
  { value: "system_admin", label: "Sistem yöneticisi" },
];
const EMPTY_FORM: UserCreateInput = {
  email: "",
  full_name: "",
  role: "dentist",
  clinic_id: "",
  reason: "",
};

type StatusFilter = "all" | "active" | "inactive";

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function UsersPage() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [clinics, setClinics] = useState<Clinic[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("active");
  const [roleFilter, setRoleFilter] = useState<RoleCode | "">("");
  const [clinicFilter, setClinicFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState<UserCreateInput>(EMPTY_FORM);
  const [temporaryPassword, setTemporaryPassword] = useState<{
    email: string;
    password: string;
  } | null>(null);
  const [copyMessage, setCopyMessage] = useState<string | null>(null);
  const [statusTarget, setStatusTarget] = useState<ManagedUser | null>(null);
  const [statusReason, setStatusReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const clinicNames = useMemo(
    () => new Map(clinics.map((clinic) => [clinic.id, clinic.name])),
    [clinics],
  );
  const activeClinics = useMemo(
    () => clinics.filter((clinic) => clinic.is_active),
    [clinics],
  );

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listUsers({
        search,
        isActive: statusFilter === "all" ? undefined : statusFilter === "active",
        role: roleFilter || undefined,
        clinicId: clinicFilter || undefined,
        limit: PAGE_SIZE,
        offset,
      });
      setUsers(result.items);
      setTotal(result.total);
    } catch (loadError) {
      setError(userErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, [clinicFilter, offset, roleFilter, search, statusFilter]);

  useEffect(() => {
    // Remote list synchronization is intentionally performed in this effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadUsers();
  }, [loadUsers]);

  useEffect(() => {
    let active = true;
    void listClinics({ limit: 100, offset: 0 })
      .then((result) => {
        if (active) setClinics(result.items);
      })
      .catch((clinicError) => {
        if (active) setError(userErrorMessage(clinicError));
      });
    return () => {
      active = false;
    };
  }, []);

  function applySearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setOffset(0);
    setSearch(searchInput.trim());
  }

  function openCreateForm() {
    setForm({ ...EMPTY_FORM, clinic_id: activeClinics[0]?.id ?? "" });
    setCreateOpen(true);
    setError(null);
    setNotice(null);
  }

  async function submitCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const result = await createUser(form);
      setCreateOpen(false);
      setTemporaryPassword({
        email: result.user.email,
        password: result.temporary_password,
      });
      setCopyMessage(null);
      setNotice(`${result.user.full_name} başarıyla oluşturuldu.`);
      await loadUsers();
    } catch (submitError) {
      setError(userErrorMessage(submitError));
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
      await changeUserStatus(statusTarget.id, !statusTarget.is_active, statusReason);
      setNotice(
        statusTarget.is_active
          ? "Kullanıcı pasifleştirildi ve Firebase girişi kapatıldı."
          : "Kullanıcı yeniden etkinleştirildi.",
      );
      setStatusTarget(null);
      setStatusReason("");
      await loadUsers();
    } catch (statusError) {
      setError(userErrorMessage(statusError));
    } finally {
      setSubmitting(false);
    }
  }

  async function copyTemporaryPassword() {
    if (temporaryPassword === null) return;
    try {
      await navigator.clipboard.writeText(temporaryPassword.password);
      setCopyMessage("Geçici parola panoya kopyalandı.");
    } catch {
      setCopyMessage("Parola kopyalanamadı; metni seçerek kopyalayabilirsiniz.");
    }
  }

  const requiresClinic = !GLOBAL_ROLES.has(form.role);
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
            <h1>Kullanıcılar</h1>
            <p>Personel hesaplarını oluşturun, rollerini görün ve erişimlerini yönetin.</p>
          </div>
          <button className="primary-button compact-button" onClick={openCreateForm}>
            + Yeni kullanıcı
          </button>
        </div>

        {notice !== null && <div className="success-message" role="status">{notice}</div>}
        {error !== null && <div className="form-error" role="alert">{error}</div>}

        <section className="management-card">
          <div className="filters-row user-filters">
            <form className="search-form" onSubmit={applySearch}>
              <label className="sr-only" htmlFor="user-search">Kullanıcı ara</label>
              <input
                id="user-search"
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
                placeholder="Ad soyad veya e-posta"
              />
              <button className="secondary-button" type="submit">Ara</button>
            </form>
            <label className="filter-select">
              <span>Rol</span>
              <select value={roleFilter} onChange={(event) => { setRoleFilter(event.target.value as RoleCode | ""); setOffset(0); }}>
                <option value="">Tümü</option>
                {FILTER_ROLE_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            </label>
            <label className="filter-select">
              <span>Klinik</span>
              <select value={clinicFilter} onChange={(event) => { setClinicFilter(event.target.value); setOffset(0); }}>
                <option value="">Tümü</option>
                {clinics.map((clinic) => <option key={clinic.id} value={clinic.id}>{clinic.name}</option>)}
              </select>
            </label>
            <label className="filter-select">
              <span>Durum</span>
              <select value={statusFilter} onChange={(event) => { setStatusFilter(event.target.value as StatusFilter); setOffset(0); }}>
                <option value="active">Aktif</option>
                <option value="inactive">Pasif</option>
                <option value="all">Tümü</option>
              </select>
            </label>
          </div>

          {loading ? (
            <div className="table-state">Kullanıcılar yükleniyor…</div>
          ) : users.length === 0 ? (
            <div className="table-state">Bu filtrelerle eşleşen kullanıcı bulunamadı.</div>
          ) : (
            <div className="table-scroll">
              <table className="data-table user-table">
                <thead><tr><th>Kullanıcı</th><th>Roller</th><th>Durum</th><th>Oluşturulma</th><th /></tr></thead>
                <tbody>
                  {users.map((managedUser) => (
                    <tr key={managedUser.id}>
                      <td><strong>{managedUser.full_name}</strong><small>{managedUser.email}</small></td>
                      <td>
                        <div className="assignment-list">
                          {managedUser.role_assignments.map((assignment) => (
                            <span className={assignment.is_active ? "" : "inactive"} key={assignment.id}>
                              {ROLE_LABELS[assignment.role]}
                              {assignment.clinic_id !== null && ` · ${clinicNames.get(assignment.clinic_id) ?? "Bilinmeyen klinik"}`}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td><span className={`state-chip ${managedUser.is_active ? "active" : "inactive"}`}>{managedUser.is_active ? "Aktif" : "Pasif"}</span></td>
                      <td><small>{formatDate(managedUser.created_at)}</small></td>
                      <td>
                        <div className="row-actions">
                          {managedUser.id === currentUser?.id ? (
                            <span className="current-account-label">Mevcut hesap</span>
                          ) : (
                            <button
                              className={managedUser.is_active ? "danger-action" : "success-action"}
                              onClick={() => { setStatusTarget(managedUser); setStatusReason(""); setError(null); }}
                            >
                              {managedUser.is_active ? "Pasife al" : "Etkinleştir"}
                            </button>
                          )}
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

      {createOpen && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal-card" role="dialog" aria-modal="true" aria-labelledby="user-form-title">
            <div className="modal-heading">
              <div><p className="eyebrow">PERSONEL HESABI</p><h2 id="user-form-title">Yeni kullanıcı</h2></div>
              <button className="icon-button" onClick={() => setCreateOpen(false)} aria-label="Pencereyi kapat">×</button>
            </div>
            <form className="management-form" onSubmit={submitCreate}>
              {error !== null && <div className="form-error" role="alert">{error}</div>}
              <label>Ad soyad<input value={form.full_name} onChange={(event) => setForm({ ...form, full_name: event.target.value })} maxLength={200} required autoFocus /></label>
              <label>E-posta<input type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} maxLength={320} required /></label>
              <label>Rol
                <select
                  value={form.role}
                  onChange={(event) => {
                    const role = event.target.value as RoleCode;
                    setForm({ ...form, role, clinic_id: GLOBAL_ROLES.has(role) ? "" : (form.clinic_id || activeClinics[0]?.id || "") });
                  }}
                >
                  {ASSIGNABLE_ROLE_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                </select>
              </label>
              {requiresClinic && (
                <label>Klinik
                  <select value={form.clinic_id} onChange={(event) => setForm({ ...form, clinic_id: event.target.value })} required>
                    <option value="" disabled>Klinik seçiniz</option>
                    {activeClinics.map((clinic) => <option key={clinic.id} value={clinic.id}>{clinic.name}</option>)}
                  </select>
                </label>
              )}
              <label>Oluşturma gerekçesi <span className="optional-label">İsteğe bağlı</span><textarea value={form.reason} onChange={(event) => setForm({ ...form, reason: event.target.value })} rows={2} maxLength={2000} /></label>
              <p className="form-hint">Firebase hesabı otomatik açılır. Geçici parola işlemden sonra yalnızca bir kez gösterilir.</p>
              <div className="modal-actions"><button type="button" className="secondary-button" onClick={() => setCreateOpen(false)}>Vazgeç</button><button className="primary-button compact-button" disabled={submitting}>{submitting ? "Oluşturuluyor…" : "Kullanıcı oluştur"}</button></div>
            </form>
          </section>
        </div>
      )}

      {temporaryPassword !== null && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal-card modal-card-small" role="dialog" aria-modal="true" aria-labelledby="credential-title">
            <div className="modal-heading"><div><p className="eyebrow">TEK SEFERLİK BİLGİ</p><h2 id="credential-title">Geçici parola</h2></div></div>
            <div className="credential-warning">Bu parola tekrar gösterilemez. Güvenli biçimde kullanıcıya iletin.</div>
            <dl className="credential-fields">
              <div><dt>E-posta</dt><dd>{temporaryPassword.email}</dd></div>
              <div><dt>Geçici parola</dt><dd className="temporary-password">{temporaryPassword.password}</dd></div>
            </dl>
            {copyMessage !== null && <div className="success-message credential-copy-message" role="status">{copyMessage}</div>}
            <div className="modal-actions"><button className="secondary-button" onClick={() => void copyTemporaryPassword()}>Parolayı kopyala</button><button className="primary-button compact-button" onClick={() => setTemporaryPassword(null)}>Kaydettim, kapat</button></div>
          </section>
        </div>
      )}

      {statusTarget !== null && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal-card modal-card-small" role="dialog" aria-modal="true" aria-labelledby="user-status-title">
            <div className="modal-heading"><div><p className="eyebrow">ERİŞİM DEĞİŞİKLİĞİ</p><h2 id="user-status-title">{statusTarget.is_active ? "Kullanıcıyı pasifleştir" : "Kullanıcıyı etkinleştir"}</h2></div><button className="icon-button" onClick={() => setStatusTarget(null)} aria-label="Pencereyi kapat">×</button></div>
            <p><strong>{statusTarget.full_name}</strong> için bu işlem Firebase ve PostgreSQL üzerinde uygulanıp audit kaydına yazılacaktır.</p>
            <form className="management-form" onSubmit={submitStatusChange}>
              {error !== null && <div className="form-error" role="alert">{error}</div>}
              <label>Gerekçe<textarea value={statusReason} onChange={(event) => setStatusReason(event.target.value)} minLength={3} maxLength={2000} rows={3} required autoFocus /></label>
              <div className="modal-actions"><button type="button" className="secondary-button" onClick={() => setStatusTarget(null)}>Vazgeç</button><button className="primary-button compact-button" disabled={submitting}>{submitting ? "İşleniyor…" : "Onayla"}</button></div>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}
