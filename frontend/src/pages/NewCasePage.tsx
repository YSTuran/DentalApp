import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { DemoBanner } from "../components/DemoBanner";
import { OperationsHeader } from "../components/OperationsHeader";
import {
  DynamicFieldsEditor,
  type DynamicFieldRow,
} from "../components/cases/DynamicFieldsEditor";
import { useResumableUpload } from "../hooks/useResumableUpload";
import { fieldsToObject, parseToothNumbers } from "../lib/case-form";
import { createCase, getCaseCreateOptions } from "../lib/cases-api";
import type { CaseCreateOptions, DentalCase } from "../types/case";

export function NewCasePage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [options, setOptions] = useState<CaseCreateOptions | null>(null);
  const [clinicId, setClinicId] = useState("");
  const [dentistId, setDentistId] = useState("");
  const [patientCode, setPatientCode] = useState("");
  const [patientName, setPatientName] = useState("");
  const [applianceType, setApplianceType] = useState("");
  const [material, setMaterial] = useState("");
  const [toothNumbers, setToothNumbers] = useState("");
  const [notes, setNotes] = useState("");
  const [reason, setReason] = useState("");
  const [extraFields, setExtraFields] = useState<DynamicFieldRow[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [created, setCreated] = useState<DentalCase | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const uploader = useResumableUpload(user?.id ?? "anonymous");

  useEffect(() => {
    getCaseCreateOptions()
      .then((result) => {
        setOptions(result);
        const firstClinic = result.clinics[0];
        if (firstClinic) {
          setClinicId(firstClinic.id);
          const self = firstClinic.dentists.find((dentist) => dentist.id === user?.id);
          setDentistId(self?.id ?? firstClinic.dentists[0]?.id ?? "");
        }
      })
      .catch(() => setError("Vaka oluşturma seçenekleri yüklenemedi."));
  }, [user?.id]);

  const selectedClinic = useMemo(
    () => options?.clinics.find((clinic) => clinic.id === clinicId),
    [clinicId, options],
  );

  function changeClinic(value: string) {
    setClinicId(value);
    const clinic = options?.clinics.find((item) => item.id === value);
    const self = clinic?.dentists.find((dentist) => dentist.id === user?.id);
    setDentistId(self?.id ?? clinic?.dentists[0]?.id ?? "");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!user || !clinicId || !dentistId) return;
    setSaving(true);
    setError(null);
    try {
      const dentalCase = created ?? await createCase({
        clinic_id: clinicId,
        responsible_dentist_user_id: dentistId,
        patient_code: patientCode.trim() || null,
        patient_name: patientName.trim() || null,
        appliance_type: applianceType || null,
        material: material || null,
        tooth_numbers: parseToothNumbers(toothNumbers),
        special_notes: notes.trim() || null,
        extra_fields: fieldsToObject(extraFields),
        reason: reason.trim() || null,
      });
      setCreated(dentalCase);
      if (file) {
        const result = await uploader.upload(dentalCase.id, file);
        if (!result) return;
      }
      navigate(`/vakalar/${dentalCase.id}`, { replace: true });
    } catch {
      setError("Vaka oluşturulamadı. Zorunlu alanları ve diş numaralarını kontrol edin.");
    } finally {
      setSaving(false);
    }
  }

  const noAccess = options !== null && options.clinics.length === 0;

  return (
    <div className="dashboard-shell">
      <DemoBanner />
      <OperationsHeader />
      <main className="management-content narrow-content">
        <div className="page-heading">
          <div><p className="eyebrow">YENİ KAYIT</p><h1>Yeni vaka oluştur</h1><p>Vaka taslak olarak açılır; geçerli STL olmadan yöneticiye gönderilemez.</p></div>
          <Link className="text-link" to="/vakalar">Vakalara dön</Link>
        </div>
        <div className="demo-data-warning"><strong>Yalnızca tanıtım verisi kullanın.</strong> Bu MVP ekranına gerçek hasta bilgisi girmeyin.</div>
        {error && <div className="form-error dashboard-error" role="alert">{error}</div>}
        {noAccess ? (
          <section className="case-panel"><h2>Vaka oluşturma yetkiniz bulunmuyor</h2><p className="panel-description">Aktif bir klinik rolü için sistem yöneticinize başvurun.</p></section>
        ) : (
          <form className="case-form case-panel" onSubmit={(event) => void handleSubmit(event)}>
            {created && (
              <div className="success-message">
                {created.case_number} taslak olarak kaydedildi. Form alanları kilitlendi; aynı STL dosyasıyla yüklemeye devam edebilirsiniz.
              </div>
            )}
            <div className="form-section-heading"><span>1</span><div><h2>Klinik ve sorumlu hekim</h2><p>Vaka yalnızca seçilen kliniğin iş akışında görünür.</p></div></div>
            <div className="form-grid two-columns">
              <label>Klinik *<select required value={clinicId} onChange={(event) => changeClinic(event.target.value)} disabled={saving || created !== null}>
                <option value="">Klinik seçin</option>
                {options?.clinics.map((clinic) => <option value={clinic.id} key={clinic.id}>{clinic.name} ({clinic.code})</option>)}
              </select></label>
              <label>Sorumlu hekim *<select required value={dentistId} onChange={(event) => setDentistId(event.target.value)} disabled={saving || created !== null}>
                <option value="">Hekim seçin</option>
                {selectedClinic?.dentists.map((dentist) => <option value={dentist.id} key={dentist.id}>{dentist.full_name}</option>)}
              </select></label>
            </div>

            <div className="form-section-heading"><span>2</span><div><h2>Vaka bilgileri</h2><p>Yıldızlı alanlar onaya gönderme aşamasında zorunludur.</p></div></div>
            <div className="form-grid two-columns">
              <label>Hasta kodu *<input disabled={saving || created !== null} value={patientCode} onChange={(event) => setPatientCode(event.target.value)} placeholder="Örn. DEMO-001" /></label>
              <label>Hasta adı (demo)<input disabled={saving || created !== null} value={patientName} onChange={(event) => setPatientName(event.target.value)} placeholder="Uydurma ad soyad" /></label>
              <label>Aparey tipi *<select disabled={saving || created !== null} value={applianceType} onChange={(event) => setApplianceType(event.target.value)}>
                <option value="">Seçin</option><option>Şeffaf plak</option><option>Gece plağı</option><option>Retainer</option><option>Splint</option><option>Diğer</option>
              </select></label>
              <label>Malzeme *<select disabled={saving || created !== null} value={material} onChange={(event) => setMaterial(event.target.value)}>
                <option value="">Seçin</option><option>TPU</option><option>PET-G</option><option>PMMA</option><option>Reçine</option><option>Diğer</option>
              </select></label>
              <label className="full-column">Diş numaraları *<input disabled={saving || created !== null} value={toothNumbers} onChange={(event) => setToothNumbers(event.target.value)} placeholder="11, 12, 13, 21 (FDI)" /><small>Virgül veya boşlukla ayırın.</small></label>
              <label className="full-column">Özel notlar<textarea disabled={saving || created !== null} rows={4} value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Laboratuvar için klinik notlar" /></label>
            </div>
            <DynamicFieldsEditor fields={extraFields} onChange={setExtraFields} disabled={saving || created !== null} />
            <label>Oluşturma gerekçesi / notu<input disabled={saving || created !== null} value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Audit kaydında görünür (isteğe bağlı)" /></label>

            <div className="form-section-heading"><span>3</span><div><h2>STL taraması</h2><p>Dosyayı şimdi yükleyebilir veya vakayı taslak kaydedip sonra ekleyebilirsiniz.</p></div></div>
            <input type="file" accept=".stl,model/stl" disabled={saving} onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
            {uploader.phase !== "idle" && <div className="upload-progress"><div><span style={{ width: `${uploader.progress}%` }} /></div><p>%{uploader.progress} yüklendi</p></div>}
            {uploader.error && <div className="form-error" role="alert">{uploader.error}</div>}
            {created && uploader.phase === "error" && <Link className="primary-link" to={`/vakalar/${created.id}`}>Taslak vakaya git</Link>}
            <div className="form-actions sticky-form-actions">
              <Link className="secondary-button link-button" to="/vakalar">Vazgeç</Link>
              <button className="primary-button" type="submit" disabled={saving || !options || noAccess}>
                {saving
                  ? (uploader.phase === "uploading" ? `STL yükleniyor · %${uploader.progress}` : "Kaydediliyor…")
                  : created
                    ? "STL yüklemesine devam et"
                    : file ? "Vakayı oluştur ve STL'yi yükle" : "Taslak oluştur"}
              </button>
            </div>
          </form>
        )}
      </main>
    </div>
  );
}
