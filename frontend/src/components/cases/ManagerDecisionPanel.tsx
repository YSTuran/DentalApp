import { useState } from "react";

import { ApiError } from "../../lib/api";
import { managerDecideCase } from "../../lib/cases-api";
import type { CurrentUser } from "../../types/auth";
import type { CaseDecision, CaseFileVersion, DentalCase } from "../../types/case";

interface Props {
  dentalCase: DentalCase;
  user: CurrentUser;
  onUpdated: (updated: DentalCase, message: string) => void;
}

const decisionContent: Record<CaseDecision, { title: string; description: string; button: string }> = {
  approved: {
    title: "Taramayı onayla",
    description: "Seçili tarama sürümü kilitlenecek ve vaka laboratuvar tasarım kuyruğuna aktarılacak.",
    button: "Onayı kesinleştir",
  },
  revision_requested: {
    title: "Düzeltme iste",
    description: "Vaka kliniğe geri dönecek ve yeni bir STL sürümü yüklenmesi beklenecek.",
    button: "Düzeltme iste",
  },
  rejected: {
    title: "Vakayı kesin reddet",
    description: "Vaka kesin ret durumuna geçecek. Bu karar normal iş akışından geri alınamaz.",
    button: "Vakayı reddet",
  },
};

function latestScan(files: CaseFileVersion[]): CaseFileVersion | null {
  const scans = files.filter((file) => file.kind === "scan");
  return scans.sort((left, right) => right.version_number - left.version_number)[0] ?? null;
}

export function ManagerDecisionPanel({ dentalCase, user, onUpdated }: Props) {
  const [decision, setDecision] = useState<CaseDecision | null>(null);
  const [reason, setReason] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scan = latestScan(dentalCase.file_versions);
  const isSelfApproval = user.id === dentalCase.created_by_user_id;

  function open(nextDecision: CaseDecision) {
    setDecision(nextDecision);
    setReason("");
    setConfirmed(false);
    setError(null);
  }

  function close() {
    if (saving) return;
    setDecision(null);
  }

  async function submitDecision() {
    if (!decision || !scan) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await managerDecideCase(
        dentalCase.id,
        decision,
        scan.id,
        reason.trim() || null,
      );
      const messages: Record<CaseDecision, string> = {
        approved: "Tarama onaylandı ve vaka laboratuvar tasarımına aktarıldı.",
        revision_requested: "Düzeltme talebi kliniğe iletildi.",
        rejected: "Vaka kesin olarak reddedildi.",
      };
      setDecision(null);
      onUpdated(updated, messages[decision]);
    } catch (caught) {
      if (caught instanceof ApiError && caught.detail === "case_scan_version_changed") {
        setError("İncelediğiniz sırada tarama sürümü değişti. Vakayı yenileyip son sürümü kontrol edin.");
      } else {
        setError("Karar kaydedilemedi. Yetkinizi ve vakanın güncel durumunu kontrol edin.");
      }
    } finally {
      setSaving(false);
    }
  }

  const reasonRequired = decision !== null && decision !== "approved";
  const canSubmit = decision !== null
    && !saving
    && (!reasonRequired || reason.trim().length >= 3)
    && (decision !== "approved" || confirmed);

  return (
    <>
      <section className="case-panel manager-decision-panel">
        <p className="card-label">YÖNETİCİ HEKİM KARARI</p>
        <h2>Tarama incelemesi</h2>
        <p className="panel-description">
          Karar yalnızca en son tarama sürümüne bağlanır ve daha sonra değiştirilemez.
        </p>
        {isSelfApproval && (
          <div className="self-approval-warning">
            Bu vaka size ait. Onay verirseniz kayıt “yönetici kendi vakasını onayladı” olarak işaretlenecek.
          </div>
        )}
        {!scan || scan.mesh_status !== "valid" ? (
          <div className="form-error">Karar verilebilmesi için geçerli bir tarama sürümü gerekiyor.</div>
        ) : (
          <div className="manager-decision-actions">
            <button className="primary-button" type="button" onClick={() => open("approved")}>Onayla</button>
            <button className="secondary-button revision-button" type="button" onClick={() => open("revision_requested")}>Düzeltme iste</button>
            <button className="secondary-button danger-button" type="button" onClick={() => open("rejected")}>Kesin reddet</button>
          </div>
        )}
      </section>

      {decision && scan && (
        <div className="modal-backdrop" role="presentation" onMouseDown={(event) => {
          if (event.target === event.currentTarget) close();
        }}>
          <section className="modal-card modal-card-small decision-modal" role="dialog" aria-modal="true" aria-labelledby="decision-title">
            <div className="modal-heading">
              <div><p className="card-label">TARAMA v{scan.version_number}</p><h2 id="decision-title">{decisionContent[decision].title}</h2></div>
              <button className="icon-button" type="button" aria-label="Pencereyi kapat" onClick={close}>×</button>
            </div>
            <p>{decisionContent[decision].description}</p>
            <label className="decision-reason">
              {reasonRequired ? "Karar gerekçesi *" : "Onay notu (isteğe bağlı)"}
              <textarea rows={4} value={reason} maxLength={2000} disabled={saving} onChange={(event) => setReason(event.target.value)} placeholder={reasonRequired ? "En az 3 karakter açıklama yazın" : "Audit kaydında görünecek not"} />
            </label>
            {decision === "approved" && (
              <label className="irreversible-check">
                <input type="checkbox" checked={confirmed} disabled={saving} onChange={(event) => setConfirmed(event.target.checked)} />
                <span>Onayın geri alınamayacağını ve bu STL sürümünün kilitleneceğini onaylıyorum.</span>
              </label>
            )}
            {error && <div className="form-error" role="alert">{error}</div>}
            <div className="modal-actions">
              <button className="secondary-button" type="button" disabled={saving} onClick={close}>Vazgeç</button>
              <button className={decision === "rejected" ? "primary-button destructive-primary" : "primary-button"} type="button" disabled={!canSubmit} onClick={() => void submitDecision()}>
                {saving ? "Kaydediliyor…" : decisionContent[decision].button}
              </button>
            </div>
          </section>
        </div>
      )}
    </>
  );
}
