import { useMemo, useState, type FormEvent } from "react";

import { ApiError } from "../../lib/api";
import { fieldsToObject, objectToFields, parseToothNumbers } from "../../lib/case-form";
import { getCaseCreateOptions, updateCase } from "../../lib/cases-api";
import type { CaseCreateOptions, CaseWritePayload, DentalCase } from "../../types/case";
import { DynamicFieldsEditor, type DynamicFieldRow } from "./DynamicFieldsEditor";

interface Props {
  dentalCase: DentalCase;
  onUpdated: (updated: DentalCase, message: string) => void;
}

type UpdatePayload = Omit<CaseWritePayload, "clinic_id">;

export function CaseEditDialog({ dentalCase, onUpdated }: Props) {
  const [open, setOpen] = useState(false);
  const [options, setOptions] = useState<CaseCreateOptions | null>(null);
  const [dentistId, setDentistId] = useState("");
  const [patientCode, setPatientCode] = useState("");
  const [patientName, setPatientName] = useState("");
  const [applianceType, setApplianceType] = useState("");
  const [material, setMaterial] = useState("");
  const [toothNumbers, setToothNumbers] = useState("");
  const [notes, setNotes] = useState("");
  const [extraFields, setExtraFields] = useState<DynamicFieldRow[]>([]);
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const dentists = useMemo(
    () => options?.clinics.find((clinic) => clinic.id === dentalCase.clinic_id)?.dentists ?? [],
    [dentalCase.clinic_id, options],
  );

  const payload = useMemo<UpdatePayload>(() => ({
    responsible_dentist_user_id: dentistId,
    patient_code: patientCode.trim() || null,
    patient_name: patientName.trim() || null,
    appliance_type: applianceType || null,
    material: material || null,
    tooth_numbers: parseToothNumbers(toothNumbers),
    special_notes: notes.trim() || null,
    extra_fields: fieldsToObject(extraFields),
  }), [
    applianceType,
    dentistId,
    extraFields,
    material,
    notes,
    patientCode,
    patientName,
    toothNumbers,
  ]);

  const originalPayload = useMemo<UpdatePayload>(() => ({
    responsible_dentist_user_id: dentalCase.responsible_dentist_user_id ?? "",
    patient_code: dentalCase.patient_code ?? null,
    patient_name: dentalCase.patient_name ?? null,
    appliance_type: dentalCase.details.appliance_type,
    material: dentalCase.details.material,
    tooth_numbers: dentalCase.details.tooth_numbers,
    special_notes: dentalCase.details.special_notes,
    extra_fields: Object.fromEntries(
      Object.entries(dentalCase.details.extra_fields).map(([key, value]) => [key, String(value)]),
    ),
  }), [dentalCase]);

  const changed = JSON.stringify(payload) !== JSON.stringify(originalPayload);

  async function show() {
    setDentistId(dentalCase.responsible_dentist_user_id ?? "");
    setPatientCode(dentalCase.patient_code ?? "");
    setPatientName(dentalCase.patient_name ?? "");
    setApplianceType(dentalCase.details.appliance_type ?? "");
    setMaterial(dentalCase.details.material ?? "");
    setToothNumbers(dentalCase.details.tooth_numbers.join(", "));
    setNotes(dentalCase.details.special_notes ?? "");
    setExtraFields(objectToFields(dentalCase.details.extra_fields));
    setReason("");
    setError(null);
    setOpen(true);
    if (options === null) {
      try {
        setOptions(await getCaseCreateOptions());
      } catch {
        setError("Hekim seçenekleri yüklenemedi. Diğer alanları yine düzenleyebilirsiniz.");
      }
    }
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!changed || !dentistId) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await updateCase(dentalCase.id, {
        ...payload,
        reason: reason.trim() || null,
      });
      setOpen(false);
      onUpdated(updated, "Taslak vaka bilgileri güncellendi.");
    } catch (caught) {
      if (caught instanceof ApiError && caught.detail === "case_no_changes") {
        setError("Kaydedilecek bir değişiklik bulunmuyor.");
      } else {
        setError("Vaka güncellenemedi. Alanları ve yetkinizi kontrol edin.");
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <button className="secondary-button compact-button" type="button" onClick={() => void show()}>
        Taslağı düzenle
      </button>
      {open && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal-card case-edit-modal" role="dialog" aria-modal="true" aria-labelledby="case-edit-title">
            <div className="modal-heading">
              <div><p className="eyebrow">{dentalCase.case_number}</p><h2 id="case-edit-title">Taslak bilgilerini düzenle</h2></div>
              <button className="icon-button" type="button" aria-label="Pencereyi kapat" disabled={saving} onClick={() => setOpen(false)}>×</button>
            </div>
            <form className="case-form" onSubmit={(event) => void save(event)}>
              <div className="form-grid two-columns">
                <label>Sorumlu hekim *
                  <select required value={dentistId} disabled={saving || dentists.length === 0} onChange={(event) => setDentistId(event.target.value)}>
                    {dentists.length === 0 && <option value={dentistId}>{dentalCase.responsible_dentist_name ?? "Mevcut hekim"}</option>}
                    {dentists.map((dentist) => <option key={dentist.id} value={dentist.id}>{dentist.full_name}</option>)}
                  </select>
                </label>
                <label>Hasta kodu *<input value={patientCode} maxLength={100} disabled={saving} onChange={(event) => setPatientCode(event.target.value)} /></label>
                <label>Hasta adı (demo)<input value={patientName} maxLength={200} disabled={saving} onChange={(event) => setPatientName(event.target.value)} /></label>
                <label>Aparey tipi *<select value={applianceType} disabled={saving} onChange={(event) => setApplianceType(event.target.value)}><option value="">Seçin</option><option>Şeffaf plak</option><option>Gece plağı</option><option>Retainer</option><option>Splint</option><option>Diğer</option></select></label>
                <label>Malzeme *<select value={material} disabled={saving} onChange={(event) => setMaterial(event.target.value)}><option value="">Seçin</option><option>TPU</option><option>PET-G</option><option>PMMA</option><option>Reçine</option><option>Diğer</option></select></label>
                <label className="full-column">Diş numaraları *<input value={toothNumbers} disabled={saving} onChange={(event) => setToothNumbers(event.target.value)} /><small>FDI numaralarını virgül veya boşlukla ayırın.</small></label>
                <label className="full-column">Özel notlar<textarea rows={3} maxLength={5000} value={notes} disabled={saving} onChange={(event) => setNotes(event.target.value)} /></label>
              </div>
              <DynamicFieldsEditor fields={extraFields} onChange={setExtraFields} disabled={saving} />
              <label>Değişiklik notu <span className="optional-label">İsteğe bağlı</span><textarea rows={2} maxLength={2000} value={reason} disabled={saving} onChange={(event) => setReason(event.target.value)} /></label>
              {error && <div className="form-error" role="alert">{error}</div>}
              <div className="modal-actions">
                <button className="secondary-button" type="button" disabled={saving} onClick={() => setOpen(false)}>Vazgeç</button>
                <button className="primary-button" type="submit" disabled={saving || !changed || !dentistId}>{saving ? "Kaydediliyor…" : "Değişiklikleri kaydet"}</button>
              </div>
            </form>
          </section>
        </div>
      )}
    </>
  );
}
