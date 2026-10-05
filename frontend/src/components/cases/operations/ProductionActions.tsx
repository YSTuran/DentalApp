import { useState } from "react";

import { completeProduction, createShipment, startProduction } from "../../../lib/fulfillment-api";
import type { DentalCase } from "../../../types/case";
import type { ProductionRun } from "../../../types/fulfillment";

interface ActionProps {
  dentalCase: DentalCase;
  onUpdated: (updated: DentalCase, message: string) => void;
}

interface RunActionProps extends ActionProps {
  productionRun: ProductionRun;
}

function ActionError({ message }: { message: string | null }) {
  return message ? <div className="form-error" role="alert">{message}</div> : null;
}

export function ProductionStartAction({ dentalCase, onUpdated }: ActionProps) {
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const design = [...dentalCase.file_versions]
    .filter((file) => file.kind === "design" && file.is_locked)
    .sort((left, right) => right.version_number - left.version_number)[0];

  async function submit() {
    if (!design) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await startProduction(dentalCase.id, design.id, notes.trim() || null);
      onUpdated(updated, "Üretim başlatıldı ve iş emri oluşturuldu.");
    } catch {
      setError("Üretim başlatılamadı. Onaylı ve kilitli tasarım sürümünü kontrol edin.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="operation-action">
      <h3>Üretimi başlat</h3>
      <p>Onaylı tasarım için yeni ve değiştirilemez bir üretim denemesi oluşturulur.</p>
      <label>Üretim notu<textarea rows={3} maxLength={2000} value={notes} disabled={saving} onChange={(event) => setNotes(event.target.value)} /></label>
      <ActionError message={design ? error : "Kilitli ve onaylı tasarım sürümü bulunamadı."} />
      <button className="primary-button" type="button" disabled={!design || saving} onClick={() => void submit()}>{saving ? "Başlatılıyor…" : "Üretimi başlat"}</button>
    </div>
  );
}

export function ProductionCompleteAction({ dentalCase, productionRun, onUpdated }: RunActionProps) {
  const [material, setMaterial] = useState(dentalCase.details.material ?? "");
  const [lotNumber, setLotNumber] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const valid = material.trim() !== "" && lotNumber.trim() !== "" && quantity > 0;

  async function submit() {
    if (!valid) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await completeProduction(dentalCase.id, productionRun.id, {
        material: material.trim(),
        lot_number: lotNumber.trim(),
        quantity,
        notes: notes.trim() || null,
      });
      onUpdated(updated, "Üretim tamamlandı; malzeme ve lot bilgisi kaydedildi.");
    } catch {
      setError("Üretim tamamlanamadı. Lot bilgisini ve vaka durumunu kontrol edin.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="operation-action">
      <h3>Üretimi tamamla</h3>
      <div className="operation-form-grid">
        <label>Malzeme *<input maxLength={200} value={material} disabled={saving} onChange={(event) => setMaterial(event.target.value)} /></label>
        <label>Lot numarası *<input maxLength={120} value={lotNumber} disabled={saving} onChange={(event) => setLotNumber(event.target.value)} /></label>
        <label>Adet *<input type="number" min={1} max={10000} value={quantity} disabled={saving} onChange={(event) => setQuantity(Number(event.target.value))} /></label>
      </div>
      <label>Üretim notu<textarea rows={3} maxLength={2000} value={notes} disabled={saving} onChange={(event) => setNotes(event.target.value)} /></label>
      <ActionError message={error} />
      <button className="primary-button" type="button" disabled={!valid || saving} onClick={() => void submit()}>{saving ? "Kaydediliyor…" : "Üretimi tamamla"}</button>
    </div>
  );
}

export function ShipmentCreateAction({ dentalCase, productionRun, onUpdated }: RunActionProps) {
  const [carrier, setCarrier] = useState("");
  const [trackingNumber, setTrackingNumber] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const valid = carrier.trim() !== "" && trackingNumber.trim() !== "";

  async function submit() {
    if (!valid) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await createShipment(dentalCase.id, productionRun.id, {
        carrier: carrier.trim(),
        tracking_number: trackingNumber.trim(),
        notes: notes.trim() || null,
      });
      onUpdated(updated, "Ürün kargoya verildi ve takip bilgisi kaydedildi.");
    } catch {
      setError("Kargo kaydı oluşturulamadı. Takip numarasını ve vaka durumunu kontrol edin.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="operation-action">
      <h3>Kargoya ver</h3>
      <div className="operation-form-grid">
        <label>Kargo firması *<input maxLength={120} value={carrier} disabled={saving} onChange={(event) => setCarrier(event.target.value)} /></label>
        <label>Takip numarası *<input maxLength={120} value={trackingNumber} disabled={saving} onChange={(event) => setTrackingNumber(event.target.value)} /></label>
      </div>
      <label>Gönderim notu<textarea rows={3} maxLength={2000} value={notes} disabled={saving} onChange={(event) => setNotes(event.target.value)} /></label>
      <ActionError message={error} />
      <button className="primary-button" type="button" disabled={!valid || saving} onClick={() => void submit()}>{saving ? "Kaydediliyor…" : "Kargoya verildi olarak kaydet"}</button>
    </div>
  );
}
