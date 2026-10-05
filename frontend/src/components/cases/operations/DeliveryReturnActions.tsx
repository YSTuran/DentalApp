import { useState } from "react";

import { confirmDelivery, decideReturn, registerReturn } from "../../../lib/fulfillment-api";
import type { DentalCase } from "../../../types/case";
import type { ReturnReasonCode, ReturnReceipt, ReturnResolution, Shipment } from "../../../types/fulfillment";

interface ShipmentActionProps {
  dentalCase: DentalCase;
  shipment: Shipment;
  onUpdated: (updated: DentalCase, message: string) => void;
}

interface DecisionActionProps {
  dentalCase: DentalCase;
  receipt: ReturnReceipt;
  onUpdated: (updated: DentalCase, message: string) => void;
}

const returnReasonLabels: Record<ReturnReasonCode, string> = {
  fit_issue: "Uyum sorunu",
  damaged: "Hasarlı ürün",
  manufacturing_defect: "Üretim hatası",
  other: "Diğer",
};

export function DeliveryConfirmAction({ dentalCase, shipment, onUpdated }: ShipmentActionProps) {
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setSaving(true);
    setError(null);
    try {
      const updated = await confirmDelivery(dentalCase.id, shipment.id, notes.trim() || null);
      onUpdated(updated, "Ürünün şubeye teslim edildiği doğrulandı.");
    } catch {
      setError("Teslim doğrulanamadı. Vaka durumunu veya klinik yetkinizi kontrol edin.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="operation-action">
      <h3>Şube teslimini doğrula</h3>
      <p><strong>{shipment.carrier}</strong> · {shipment.tracking_number}</p>
      <label>Teslim notu<textarea rows={3} maxLength={2000} value={notes} disabled={saving} onChange={(event) => setNotes(event.target.value)} /></label>
      {error && <div className="form-error" role="alert">{error}</div>}
      <button className="primary-button" type="button" disabled={saving} onClick={() => void submit()}>{saving ? "Kaydediliyor…" : "Teslim alındı"}</button>
    </div>
  );
}

export function ReturnReceiptAction({ dentalCase, shipment, onUpdated }: ShipmentActionProps) {
  const [reasonCode, setReasonCode] = useState<ReturnReasonCode>("fit_issue");
  const [reason, setReason] = useState("");
  const [inspectionNotes, setInspectionNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const valid = reason.trim().length >= 3;

  async function submit() {
    if (!valid) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await registerReturn(dentalCase.id, shipment.id, {
        reason_code: reasonCode,
        reason: reason.trim(),
        inspection_notes: inspectionNotes.trim() || null,
      });
      onUpdated(updated, "İade laboratuvara teslim alındı ve yönetici incelemesine gönderildi.");
    } catch {
      setError("İade kaydedilemedi. Teslim ve vaka durumunu kontrol edin.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="operation-action operation-return">
      <h3>İadeyi teslim al</h3>
      <label>İade kategorisi *<select value={reasonCode} disabled={saving} onChange={(event) => setReasonCode(event.target.value as ReturnReasonCode)}>{Object.entries(returnReasonLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      <label>İade gerekçesi *<textarea rows={3} maxLength={2000} value={reason} disabled={saving} onChange={(event) => setReason(event.target.value)} /></label>
      <label>Teknisyen inceleme notu<textarea rows={3} maxLength={2000} value={inspectionNotes} disabled={saving} onChange={(event) => setInspectionNotes(event.target.value)} /></label>
      {error && <div className="form-error" role="alert">{error}</div>}
      <button className="primary-button" type="button" disabled={!valid || saving} onClick={() => void submit()}>{saving ? "Kaydediliyor…" : "İadeyi kaydet"}</button>
    </div>
  );
}

export function ReturnDecisionAction({ dentalCase, receipt, onUpdated }: DecisionActionProps) {
  const [resolution, setResolution] = useState<ReturnResolution>("reproduction");
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const valid = reason.trim().length >= 3;

  async function submit() {
    if (!valid) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await decideReturn(
        dentalCase.id,
        receipt.id,
        resolution,
        reason.trim(),
      );
      onUpdated(
        updated,
        resolution === "reproduction"
          ? "Vaka yeniden üretim kuyruğuna gönderildi."
          : "Hekimden yeni tarama istendi.",
      );
    } catch {
      setError("İade kararı kaydedilemedi. Yetkinizi ve vaka durumunu kontrol edin.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="operation-action operation-decision">
      <h3>İade kararı</h3>
      <p>{returnReasonLabels[receipt.reason_code]}: {receipt.reason}</p>
      <label>Karar *<select value={resolution} disabled={saving} onChange={(event) => setResolution(event.target.value as ReturnResolution)}><option value="reproduction">Yeniden üretim</option><option value="rescan">Yeni tarama iste</option></select></label>
      <label>Karar gerekçesi *<textarea rows={3} maxLength={2000} value={reason} disabled={saving} onChange={(event) => setReason(event.target.value)} /></label>
      {error && <div className="form-error" role="alert">{error}</div>}
      <button className="primary-button" type="button" disabled={!valid || saving} onClick={() => void submit()}>{saving ? "Kaydediliyor…" : "Kararı kaydet"}</button>
    </div>
  );
}
