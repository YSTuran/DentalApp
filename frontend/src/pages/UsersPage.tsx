import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { useAuth } from "../auth/AuthContext";
import { DemoBanner } from "../components/DemoBanner";
import { ManagementHeader } from "../components/ManagementHeader";
import { UserClinicAddDialog } from "../components/UserClinicAddDialog";
import { UserTable } from "../components/users/UserTable";
import {
  ASSIGNABLE_ROLE_OPTIONS,
  EMPTY_USER_FORM,
  FILTER_ROLE_OPTIONS,
  GLOBAL_ROLES,
  PAGE_SIZE,
  ROLE_LABELS,
} from "../components/users/user-options";
import { listClinics } from "../lib/clinics-api";
import {
  addClinicAssignment,
  changeClinicAssignmentStatus,
  changeRoleAssignment,
  changeUserStatus,
  createUser,
  listUsers,
  userErrorMessage,
} from "../lib/users-api";
import type { RoleCode } from "../types/auth";
import type { Clinic } from "../types/clinic";
import type {
  ClinicAssignment,
  ClinicAssignmentCreateInput,
  ManagedUser,
  RoleAssignment,
  RoleAssignmentUpdateInput,
  UserCreateInput,
} from "../types/user-management";

interface RoleChangeForm extends RoleAssignmentUpdateInput {
  assignment_id: string;
}

const EMPTY_ROLE_CHANGE_FORM: RoleChangeForm = {
  assignment_id: "",
  role: "dentist",
  reason: "",
};

const EMPTY_CLINIC_ADD_FORM: ClinicAssignmentCreateInput = {
  clinic_id: "",
  reason: "",
};

type StatusFilter = "all" | "active" | "inactive";

export function UsersPage() {
  const { user: currentUser } = useAuth();
  const isSystemAdmin = currentUser?.global_roles.includes("system_admin") === true;
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [clinics, setClinics] = useState<Clinic[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("active");
  const [roleFilter, setRoleFilter] = useState<RoleCode | "">("");
  const [clinicOverride, setClinicOverride] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState<UserCreateInput>(EMPTY_USER_FORM);
  const [temporaryPassword, setTemporaryPassword] = useState<{
    email: string;
    password: string;
  } | null>(null);
  const [copyMessage, setCopyMessage] = useState<string | null>(null);
  const [statusTarget, setStatusTarget] = useState<ManagedUser | null>(null);
  const [statusReason, setStatusReason] = useState("");
  const [roleTarget, setRoleTarget] = useState<ManagedUser | null>(null);
  const [roleForm, setRoleForm] = useState<RoleChangeForm>(EMPTY_ROLE_CHANGE_FORM);
  const [clinicAddTarget, setClinicAddTarget] = useState<ManagedUser | null>(null);
  const [clinicAddForm, setClinicAddForm] = useState(EMPTY_CLINIC_ADD_FORM);
  const [clinicStatusTarget, setClinicStatusTarget] = useState<{
    user: ManagedUser;
    assignment: ClinicAssignment;
  } | null>(null);
  const [clinicStatusReason, setClinicStatusReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const clinicFilter = clinicOverride
    ?? currentUser?.preferences.active_clinic_id
    ?? "";

  const clinicNames = useMemo(
    () => new Map(clinics.map((clinic) => [clinic.id, clinic.name])),
    [clinics],
  );
  const activeClinics = useMemo(
    () => clinics.filter((clinic) => clinic.is_active),
    [clinics],
  );
  const clinicAddOptions = useMemo(() => {
    if (clinicAddTarget === null) return [];
    const assignedClinicIds = new Set(
      clinicAddTarget.clinic_assignments
        .map((assignment) => assignment.clinic_id),
    );
    return activeClinics.filter((clinic) => !assignedClinicIds.has(clinic.id));
  }, [activeClinics, clinicAddTarget]);

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
    setForm({ ...EMPTY_USER_FORM, clinic_id: activeClinics[0]?.id ?? "" });
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

  function editableAssignments(user: ManagedUser): RoleAssignment[] {
    return user.role_assignments.filter(
      (assignment) => assignment.is_active && assignment.role !== "system_admin",
    );
  }

  function openRoleForm(user: ManagedUser) {
    const assignment = editableAssignments(user)[0];
    if (assignment === undefined) return;
    setRoleTarget(user);
    setRoleForm({
      assignment_id: assignment.id,
      role: assignment.role,
      reason: "",
    });
    setError(null);
    setNotice(null);
  }

  function selectRoleAssignment(assignmentId: string) {
    if (roleTarget === null) return;
    const assignment = editableAssignments(roleTarget).find(
      (candidate) => candidate.id === assignmentId,
    );
    if (assignment === undefined) return;
    setRoleForm({
      assignment_id: assignment.id,
      role: assignment.role,
      reason: roleForm.reason,
    });
  }

  async function submitRoleChange(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (roleTarget === null) return;
    setSubmitting(true);
    setError(null);
    try {
      await changeRoleAssignment(roleTarget.id, roleForm.assignment_id, {
        role: roleForm.role,
        reason: roleForm.reason,
      });
      setNotice(`${roleTarget.full_name} için rol güncellendi.`);
      setRoleTarget(null);
      setRoleForm(EMPTY_ROLE_CHANGE_FORM);
      await loadUsers();
    } catch (roleError) {
      setError(userErrorMessage(roleError));
    } finally {
      setSubmitting(false);
    }
  }

  function openClinicAddForm(user: ManagedUser) {
    const assignedClinicIds = new Set(
      user.clinic_assignments
        .map((assignment) => assignment.clinic_id),
    );
    setClinicAddTarget(user);
    setClinicAddForm({
      ...EMPTY_CLINIC_ADD_FORM,
      clinic_id: activeClinics.find((clinic) => !assignedClinicIds.has(clinic.id))?.id ?? "",
    });
    setError(null);
    setNotice(null);
  }

  async function submitClinicAdd(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (clinicAddTarget === null) return;
    setSubmitting(true);
    setError(null);
    try {
      await addClinicAssignment(clinicAddTarget.id, clinicAddForm);
      setNotice(`${clinicAddTarget.full_name} için yeni klinik ataması eklendi.`);
      setClinicAddTarget(null);
      setClinicAddForm(EMPTY_CLINIC_ADD_FORM);
      await loadUsers();
    } catch (roleError) {
      setError(userErrorMessage(roleError));
    } finally {
      setSubmitting(false);
    }
  }

  async function submitClinicStatusChange(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (clinicStatusTarget === null) return;
    setSubmitting(true);
    setError(null);
    const { user, assignment } = clinicStatusTarget;
    try {
      await changeClinicAssignmentStatus(
        user.id,
        assignment.id,
        !assignment.is_active,
        clinicStatusReason,
      );
      setNotice(
        assignment.is_active
          ? `${user.full_name} için klinik erişimi kaldırıldı.`
          : `${user.full_name} için klinik erişimi yeniden etkinleştirildi.`,
      );
      setClinicStatusTarget(null);
      setClinicStatusReason("");
      await loadUsers();
    } catch (clinicError) {
      setError(userErrorMessage(clinicError));
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
  return (
    <div className="dashboard-shell">
      <DemoBanner />
      <ManagementHeader />
      <main className="management-content">
        <div className="page-heading">
          <div>
            <p className="eyebrow">{isSystemAdmin ? "SİSTEM YÖNETİMİ" : "KLİNİK GÖRÜNÜMÜ"}</p>
            <h1>Kullanıcılar</h1>
            <p>{isSystemAdmin ? "Personel hesaplarını oluşturun, rollerini görün ve erişimlerini yönetin." : "Kliniğinizdeki hekimleri ve yönetici hekimleri görüntüleyin."}</p>
          </div>
          {isSystemAdmin && (
            <button className="primary-button compact-button" onClick={openCreateForm}>
              + Yeni kullanıcı
            </button>
          )}
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
                {(isSystemAdmin
                  ? FILTER_ROLE_OPTIONS
                  : FILTER_ROLE_OPTIONS.filter((option) => option.value === "dentist" || option.value === "managing_dentist")
                ).map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            </label>
            <label className="filter-select">
              <span>Klinik</span>
              <select value={clinicFilter} onChange={(event) => { setClinicOverride(event.target.value); setOffset(0); }}>
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

          <UserTable
            users={users}
            clinics={activeClinics}
            clinicNames={clinicNames}
            currentUserId={currentUser?.id}
            isSystemAdmin={isSystemAdmin}
            loading={loading}
            total={total}
            offset={offset}
            onOffsetChange={setOffset}
            onRoleEdit={openRoleForm}
            onClinicAdd={openClinicAddForm}
            onClinicStatus={(user, assignment) => {
              setClinicStatusTarget({ user, assignment });
              setClinicStatusReason("");
              setError(null);
            }}
            onUserStatus={(user) => {
              setStatusTarget(user);
              setStatusReason("");
              setError(null);
            }}
          />
        </section>
      </main>

      {isSystemAdmin && createOpen && (
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

      {isSystemAdmin && temporaryPassword !== null && (
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

      {isSystemAdmin && roleTarget !== null && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal-card" role="dialog" aria-modal="true" aria-labelledby="role-change-title">
            <div className="modal-heading">
              <div><p className="eyebrow">YETKİ ATAMASI</p><h2 id="role-change-title">Rolü düzenle</h2></div>
              <button className="icon-button" onClick={() => setRoleTarget(null)} aria-label="Pencereyi kapat">×</button>
            </div>
            <p><strong>{roleTarget.full_name}</strong> için seçilen aktif atama değiştirilecektir. Eski atama silinmez; geçmişte pasif olarak saklanır.</p>
            <form className="management-form" onSubmit={submitRoleChange}>
              {error !== null && <div className="form-error" role="alert">{error}</div>}
              <label>Değiştirilecek atama
                <select value={roleForm.assignment_id} onChange={(event) => selectRoleAssignment(event.target.value)}>
                  {editableAssignments(roleTarget).map((assignment) => (
                    <option key={assignment.id} value={assignment.id}>
                      {ROLE_LABELS[assignment.role]}
                    </option>
                  ))}
                </select>
              </label>
              <label>Yeni rol
                <select
                  value={roleForm.role}
                  onChange={(event) => {
                    const role = event.target.value as RoleCode;
                    setRoleForm({ ...roleForm, role });
                  }}
                >
                  {ASSIGNABLE_ROLE_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                </select>
              </label>
              <label>Değişiklik gerekçesi
                <textarea value={roleForm.reason} onChange={(event) => setRoleForm({ ...roleForm, reason: event.target.value })} minLength={3} maxLength={2000} rows={3} required />
              </label>
              <p className="form-hint">Rol değişikliği klinik atamalarını değiştirmez ve audit kaydına yazılır. Sistem yöneticisi rolü bu ekrandan atanamaz.</p>
              <div className="modal-actions"><button type="button" className="secondary-button" onClick={() => setRoleTarget(null)}>Vazgeç</button><button className="primary-button compact-button" disabled={submitting}>{submitting ? "Güncelleniyor…" : "Değişikliği uygula"}</button></div>
            </form>
          </section>
        </div>
      )}

      {isSystemAdmin && clinicAddTarget !== null && (
        <UserClinicAddDialog
          target={clinicAddTarget}
          form={clinicAddForm}
          clinics={clinicAddOptions}
          submitting={submitting}
          error={error}
          onChange={setClinicAddForm}
          onClose={() => setClinicAddTarget(null)}
          onSubmit={submitClinicAdd}
        />
      )}

      {isSystemAdmin && clinicStatusTarget !== null && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal-card modal-card-small" role="dialog" aria-modal="true" aria-labelledby="clinic-status-title">
            <div className="modal-heading">
              <div><p className="eyebrow">KLİNİK ERİŞİMİ</p><h2 id="clinic-status-title">{clinicStatusTarget.assignment.is_active ? "Klinik erişimini kaldır" : "Klinik erişimini etkinleştir"}</h2></div>
              <button className="icon-button" onClick={() => setClinicStatusTarget(null)} aria-label="Pencereyi kapat">×</button>
            </div>
            <p><strong>{clinicStatusTarget.user.full_name}</strong> · {clinicNames.get(clinicStatusTarget.assignment.clinic_id) ?? "Bilinmeyen klinik"}</p>
            <form className="management-form" onSubmit={submitClinicStatusChange}>
              {error !== null && <div className="form-error" role="alert">{error}</div>}
              <label>Gerekçe<textarea value={clinicStatusReason} onChange={(event) => setClinicStatusReason(event.target.value)} minLength={3} maxLength={2000} rows={3} required autoFocus /></label>
              <div className="modal-actions"><button type="button" className="secondary-button" onClick={() => setClinicStatusTarget(null)}>Vazgeç</button><button className="primary-button compact-button" disabled={submitting}>{submitting ? "İşleniyor…" : "Onayla"}</button></div>
            </form>
          </section>
        </div>
      )}

      {isSystemAdmin && statusTarget !== null && (
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
