import { useState } from "react";

import { ApiError } from "../../lib/api";
import { latestCaseFile } from "../../lib/case-files";
import { dentistDecideDesign } from "../../lib/cases-api";
import type { DentalCase } from "../../types/case";

interface Props {
  dentalCase: DentalCase;
  onUpdated: (updated: DentalCase, message: string) => void;
}

type DentistDecision = "approved" | "revision_requested";

const content = {
  approved: {
    title: "Tasarımı onayla",
    description: "Seçili tasarım sürümü kilitlenecek ve vaka üretime hazır duruma geçecek.",
    button: "Onayı kesinleştir",
  },
  revision_requested: {
    title: "Tasarım düzeltmesi iste",
    description: "Vaka laboratuvara dönecek ve teknisyenden yeni bir tasarım sürümü beklenecek.",
    button: "Düzeltme iste",
  },
} satisfies Record<DentistDecision, { title: string; description: string; button: string }>;

export function DentistDesignDecisionPanel({ dentalCase, onUpdated }: Props) {
  const [decision, setDecision] = useState<DentistDecision | null>(null);
  const [reason, setReason] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const design = latestCaseFile(dentalCase.file_versions, "design");

  function show(nextDecision: DentistDecision) {
    setDecision(nextDecision);
    setReason("");
    setConfirmed(false);
    setError(null);
  }

  async function save() {
    if (!decision || !design) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await dentistDecideDesign(
        dentalCase.id,
        decision,
        design.id,
        reason.trim() || null,
      );
      setDecision(null);
      onUpdated(
        updated,
        decision === "approved"
          ? "Tasarım onaylandı; vaka üretime hazır."
          : "Tasarım düzeltme talebi laboratuvara iletildi.",
      );
    } catch (caught) {
      if (caught instanceof ApiError && caught.detail === "case_design_version_changed") {
        setError("İncelediğiniz sırada tasarım sürümü değişti. Vakayı yenileyin.");
      } else {
        setError("Karar kaydedilemedi. Yetkinizi ve vaka durumunu kontrol edin.");
      }
    } finally {
      setSaving(false);
    }
  }

  const reasonRequired = decision === "revision_requested";
  const canSave = decision !== null
    && !saving
    && (!reasonRequired || reason.trim().length >= 3)
    && (decision !== "approved" || confirmed);

  return (
    <>
      <section className="case-panel dentist-decision-panel">
        <p className="card-label">SORUMLU HEKİM ONAYI</p>
        <h2>Laboratuvar tasarımını incele</h2>
        <p className="panel-description">Kararı yalnızca bu vakanın sorumlu hekimi verebilir. Onaylanan tasarım değiştirilemez.</p>
        {!design || design.mesh_status !== "valid" ? <div className="form-error">Geçerli bir tasarım sürümü bulunmuyor.</div> : <div className="manager-decision-actions"><button className="primary-button" type="button" onClick={() => show("approved")}>Tasarımı onayla</button><button className="secondary-button revision-button" type="button" onClick={() => show("revision_requested")}>Düzeltme iste</button></div>}
      </section>
      {decision && design && <div className="modal-backdrop" role="presentation"><section className="modal-card modal-card-small decision-modal" role="dialog" aria-modal="true" aria-labelledby="dentist-decision-title"><div className="modal-heading"><div><p className="card-label">TASARIM v{design.version_number}</p><h2 id="dentist-decision-title">{content[decision].title}</h2></div><button className="icon-button" type="button" aria-label="Pencereyi kapat" disabled={saving} onClick={() => setDecision(null)}>×</button></div><p>{content[decision].description}</p><label className="decision-reason">{reasonRequired ? "Düzeltme gerekçesi *" : "Onay notu (isteğe bağlı)"}<textarea rows={4} maxLength={2000} value={reason} disabled={saving} onChange={(event) => setReason(event.target.value)} /></label>{decision === "approved" && <label className="irreversible-check"><input type="checkbox" checked={confirmed} disabled={saving} onChange={(event) => setConfirmed(event.target.checked)} /><span>Onayın geri alınamayacağını ve tasarım sürümünün kilitleneceğini onaylıyorum.</span></label>}{error && <div className="form-error" role="alert">{error}</div>}<div className="modal-actions"><button className="secondary-button" type="button" disabled={saving} onClick={() => setDecision(null)}>Vazgeç</button><button className="primary-button" type="button" disabled={!canSave} onClick={() => void save()}>{saving ? "Kaydediliyor…" : content[decision].button}</button></div></section></div>}
    </>
  );
}
