import type { Clinic } from "../../types/clinic";
import type { ClinicAssignment, ManagedUser } from "../../types/user-management";
import { PAGE_SIZE, ROLE_LABELS } from "./user-options";

interface Props {
  users: ManagedUser[];
  clinics: Clinic[];
  clinicNames: Map<string, string>;
  currentUserId?: string;
  isSystemAdmin: boolean;
  loading: boolean;
  total: number;
  offset: number;
  onOffsetChange: (offset: number) => void;
  onRoleEdit: (user: ManagedUser) => void;
  onClinicAdd: (user: ManagedUser) => void;
  onClinicStatus: (user: ManagedUser, assignment: ClinicAssignment) => void;
  onUserStatus: (user: ManagedUser) => void;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function UserTable({
  users,
  clinics,
  clinicNames,
  currentUserId,
  isSystemAdmin,
  loading,
  total,
  offset,
  onOffsetChange,
  onRoleEdit,
  onClinicAdd,
  onClinicStatus,
  onUserStatus,
}: Props) {
  const pageStart = total === 0 ? 0 : offset + 1;
  const pageEnd = Math.min(offset + PAGE_SIZE, total);

  return (
    <>
      {loading ? (
        <div className="table-state">Kullanıcılar yükleniyor…</div>
      ) : users.length === 0 ? (
        <div className="table-state">Bu filtrelerle eşleşen kullanıcı bulunamadı.</div>
      ) : (
        <div className="table-scroll">
          <table className="data-table user-table">
            <thead>
              <tr>
                <th>Kullanıcı</th><th>Rol</th><th>Klinikler</th><th>Durum</th>
                <th>Oluşturulma</th>{isSystemAdmin && <th />}
              </tr>
            </thead>
            <tbody>
              {users.map((managedUser) => {
                const activeRoles = managedUser.role_assignments.filter((item) => item.is_active);
                const editableRoles = activeRoles.filter((item) => item.role !== "system_admin");
                const canAddClinic = managedUser.is_active
                  && activeRoles.some((item) => !["system_admin", "technician"].includes(item.role))
                  && clinics.some((clinic) => !managedUser.clinic_assignments.some(
                    (item) => item.clinic_id === clinic.id,
                  ));

                return (
                  <tr key={managedUser.id}>
                    <td><strong>{managedUser.full_name}</strong><small>{managedUser.email}</small></td>
                    <td>
                      <div className="assignment-list">
                        {activeRoles.length > 0
                          ? activeRoles.map((item) => <span key={item.id}>{ROLE_LABELS[item.role]}</span>)
                          : <span>-</span>}
                      </div>
                    </td>
                    <td>
                      <div className="assignment-list clinic-assignment-list">
                        {managedUser.clinic_assignments.length > 0
                          ? managedUser.clinic_assignments.map((assignment) => (
                            <span className={assignment.is_active ? "" : "inactive"} key={assignment.id}>
                              {clinicNames.get(assignment.clinic_id) ?? "Bilinmeyen klinik"}
                              {isSystemAdmin && managedUser.id !== currentUserId && (
                                <button
                                  type="button"
                                  aria-label={`${assignment.is_active ? "Klinik erişimini kaldır" : "Klinik erişimini yeniden etkinleştir"}: ${clinicNames.get(assignment.clinic_id) ?? "Bilinmeyen klinik"}`}
                                  onClick={() => onClinicStatus(managedUser, assignment)}
                                >
                                  {assignment.is_active ? "Kaldır" : "Etkinleştir"}
                                </button>
                              )}
                            </span>
                          ))
                          : <span>-</span>}
                      </div>
                    </td>
                    <td>
                      <span className={`state-chip ${managedUser.is_active ? "active" : "inactive"}`}>
                        {managedUser.is_active ? "Aktif" : "Pasif"}
                      </span>
                    </td>
                    <td><small>{formatDate(managedUser.created_at)}</small></td>
                    {isSystemAdmin && (
                      <td>
                        <div className="row-actions">
                          {managedUser.id === currentUserId ? (
                            <span className="current-account-label">Mevcut hesap</span>
                          ) : (
                            <>
                              {managedUser.is_active && editableRoles.length > 0 && (
                                <button onClick={() => onRoleEdit(managedUser)}>Rolü düzenle</button>
                              )}
                              {canAddClinic && (
                                <button onClick={() => onClinicAdd(managedUser)}>Klinik ekle</button>
                              )}
                              <button
                                className={managedUser.is_active ? "danger-action" : "success-action"}
                                onClick={() => onUserStatus(managedUser)}
                              >
                                {managedUser.is_active ? "Pasife al" : "Etkinleştir"}
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    )}
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
          <button
            className="secondary-button"
            disabled={offset === 0 || loading}
            onClick={() => onOffsetChange(Math.max(0, offset - PAGE_SIZE))}
          >
            Önceki
          </button>
          <button
            className="secondary-button"
            disabled={offset + PAGE_SIZE >= total || loading}
            onClick={() => onOffsetChange(offset + PAGE_SIZE)}
          >
            Sonraki
          </button>
        </div>
      </div>
    </>
  );
}
