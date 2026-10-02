import { useState } from "react";

import { cancelCase } from "../../lib/cases-api";
import type { DentalCase } from "../../types/case";

interface Props {
  dentalCase: DentalCase;
  onUpdated: (updated: DentalCase, message: string) => void;
}

export function CaseCancelDialog({ dentalCase, onUpdated }: Props) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function show() {
    setReason("");
    setConfirmed(false);
    setError(null);
    setOpen(true);
  }

  async function cancel() {
    setSaving(true);
    setError(null);
    try {
      const updated = await cancelCase(dentalCase.id, reason.trim());
      setOpen(false);
      onUpdated(updated, "Vaka iptal edildi; kayıt ve geçmişi korunmaya devam ediyor.");
    } catch {
      setError("Vaka iptal edilemedi. Durumunu ve yetkinizi kontrol edin.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <button className="secondary-button danger-button compact-button" type="button" onClick={show}>Vakayı iptal et</button>
      {open && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal-card modal-card-small" role="alertdialog" aria-modal="true" aria-labelledby="case-cancel-title">
            <div className="modal-heading"><div><p className="eyebrow">KAYIT KORUNUR</p><h2 id="case-cancel-title">Vakayı iptal et</h2></div><button className="icon-button" type="button" aria-label="Pencereyi kapat" disabled={saving} onClick={() => setOpen(false)}>×</button></div>
            <p><strong>{dentalCase.case_number}</strong> silinmeyecek; iptal durumu, gerekçesi ve işlem yapan kişi audit geçmişinde saklanacaktır.</p>
            <label className="decision-reason">İptal gerekçesi *<textarea rows={4} minLength={3} maxLength={2000} value={reason} disabled={saving} onChange={(event) => setReason(event.target.value)} /></label>
            <label className="irreversible-check"><input type="checkbox" checked={confirmed} disabled={saving} onChange={(event) => setConfirmed(event.target.checked)} /><span>Bu işlemin normal iş akışından geri alınamayacağını onaylıyorum.</span></label>
            {error && <div className="form-error" role="alert">{error}</div>}
            <div className="modal-actions"><button className="secondary-button" type="button" disabled={saving} onClick={() => setOpen(false)}>Vazgeç</button><button className="primary-button destructive-primary" type="button" disabled={saving || reason.trim().length < 3 || !confirmed} onClick={() => void cancel()}>{saving ? "İptal ediliyor…" : "Vakayı iptal et"}</button></div>
          </section>
        </div>
      )}
    </>
  );
}
