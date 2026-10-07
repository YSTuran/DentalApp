import type { FormEvent } from "react";

import type { Clinic } from "../types/clinic";
import type {
  ClinicAssignmentCreateInput,
  ManagedUser,
} from "../types/user-management";

interface UserClinicAddDialogProps {
  target: ManagedUser;
  form: ClinicAssignmentCreateInput;
  clinics: Clinic[];
  submitting: boolean;
  error: string | null;
  onChange: (form: ClinicAssignmentCreateInput) => void;
  onClose: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}

export function UserClinicAddDialog({
  target,
  form,
  clinics,
  submitting,
  error,
  onChange,
  onClose,
  onSubmit,
}: UserClinicAddDialogProps) {
  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal-card" role="dialog" aria-modal="true" aria-labelledby="clinic-add-title">
        <div className="modal-heading">
          <div><p className="eyebrow">ÇOKLU KLİNİK</p><h2 id="clinic-add-title">Klinik ekle</h2></div>
          <button className="icon-button" onClick={onClose} aria-label="Pencereyi kapat">×</button>
        </div>
        <p><strong>{target.full_name}</strong> için rol değiştirilmeden yeni bir çalışma kliniği eklenecektir.</p>
        <form className="management-form" onSubmit={onSubmit}>
          {error !== null && <div className="form-error" role="alert">{error}</div>}
          <label>Yeni klinik
            <select value={form.clinic_id} onChange={(event) => onChange({ ...form, clinic_id: event.target.value })} required>
              <option value="" disabled>Klinik seçiniz</option>
              {clinics.map((clinic) => <option key={clinic.id} value={clinic.id}>{clinic.name}</option>)}
            </select>
          </label>
          <label>Atama gerekçesi <span className="optional-label">İsteğe bağlı</span>
            <textarea value={form.reason} onChange={(event) => onChange({ ...form, reason: event.target.value })} maxLength={2000} rows={3} />
          </label>
          <p className="form-hint">Klinik ataması kullanıcının rolünden bağımsızdır. Vakalarda hem hekim hem işlemin yapıldığı klinik ayrıca kaydedilir.</p>
          <div className="modal-actions">
            <button type="button" className="secondary-button" onClick={onClose}>Vazgeç</button>
            <button className="primary-button compact-button" disabled={submitting}>{submitting ? "Ekleniyor…" : "Kliniği ekle"}</button>
          </div>
        </form>
      </section>
    </div>
  );
}
