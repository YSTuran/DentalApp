import type { FormEvent } from "react";

import type { RoleCode } from "../types/auth";
import type { Clinic } from "../types/clinic";
import type {
  ManagedUser,
  RoleAssignmentUpdateInput,
} from "../types/user-management";

interface RoleOption {
  value: RoleCode;
  label: string;
}

interface UserRoleAddDialogProps {
  target: ManagedUser;
  form: RoleAssignmentUpdateInput;
  clinics: Clinic[];
  roleOptions: RoleOption[];
  submitting: boolean;
  error: string | null;
  onChange: (form: RoleAssignmentUpdateInput) => void;
  onClose: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}

export function UserRoleAddDialog({
  target,
  form,
  clinics,
  roleOptions,
  submitting,
  error,
  onChange,
  onClose,
  onSubmit,
}: UserRoleAddDialogProps) {
  const roleRequiresClinic = form.role !== "technician";

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal-card" role="dialog" aria-modal="true" aria-labelledby="role-add-title">
        <div className="modal-heading">
          <div><p className="eyebrow">YENİ YETKİ</p><h2 id="role-add-title">Rol ekle</h2></div>
          <button className="icon-button" onClick={onClose} aria-label="Pencereyi kapat">×</button>
        </div>
        <p><strong>{target.full_name}</strong> için mevcut atamalar korunarak yeni bir rol eklenecektir.</p>
        <form className="management-form" onSubmit={onSubmit}>
          {error !== null && <div className="form-error" role="alert">{error}</div>}
          <label>Yeni rol
            <select
              value={form.role}
              onChange={(event) => {
                const role = event.target.value as RoleCode;
                onChange({
                  ...form,
                  role,
                  clinic_id: role === "technician"
                    ? ""
                    : (form.clinic_id || clinics[0]?.id || ""),
                });
              }}
            >
              {roleOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </label>
          {roleRequiresClinic && (
            <label>Klinik
              <select value={form.clinic_id} onChange={(event) => onChange({ ...form, clinic_id: event.target.value })} required>
                <option value="" disabled>Klinik seçiniz</option>
                {clinics.map((clinic) => <option key={clinic.id} value={clinic.id}>{clinic.name}</option>)}
              </select>
            </label>
          )}
          <label>Atama gerekçesi <span className="optional-label">İsteğe bağlı</span>
            <textarea value={form.reason} onChange={(event) => onChange({ ...form, reason: event.target.value })} maxLength={2000} rows={3} />
          </label>
          <p className="form-hint">Birden fazla klinikte yalnızca klinik yöneticisi rolü bulunabilir. Diğer klinik rolleri tek klinikle sınırlıdır.</p>
          <div className="modal-actions">
            <button type="button" className="secondary-button" onClick={onClose}>Vazgeç</button>
            <button className="primary-button compact-button" disabled={submitting}>{submitting ? "Ekleniyor…" : "Rolü ekle"}</button>
          </div>
        </form>
      </section>
    </div>
  );
}
