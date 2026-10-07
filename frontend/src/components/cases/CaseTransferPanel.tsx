import { useCallback, useEffect, useState, type FormEvent } from "react";

import { ApiError } from "../../lib/api";
import {
  decideCaseTransfer,
  getCaseTransferOptions,
  getCaseTransfers,
  requestCaseTransfer,
} from "../../lib/cases-api";
import { formatDate } from "../../lib/case-format";
import type { CurrentUser } from "../../types/auth";
import type { CaseTransfer, CaseTransferOption, DentalCase } from "../../types/case";

interface Props {
  dentalCase: DentalCase;
  user: CurrentUser;
  onChanged: () => void;
}

const terminalStatuses = new Set(["delivered", "cancelled", "manager_rejected"]);

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const messages: Record<string, string> = {
      case_transfer_pending_exists: "Bu vaka için zaten bekleyen bir devir talebi var.",
      case_transfer_same_dentist: "Vaka mevcut sorumlu hekime devredilemez.",
      case_transfer_not_active: "Tamamlanmış veya kapatılmış vaka devredilemez.",
      case_transfer_already_decided: "Bu devir talebi daha önce sonuçlandırılmış.",
      case_transfer_source_changed: "Vakanın sorumlu hekimi değiştiği için bu talep geçersiz kaldı.",
      case_access_denied: "Bu devir işlemi için yetkiniz bulunmuyor.",
    };
    return messages[error.detail] ?? "Vaka devri tamamlanamadı.";
  }
  return "Vaka devri tamamlanamadı.";
}

export function CaseTransferPanel({ dentalCase, user, onChanged }: Props) {
  const [transfers, setTransfers] = useState<CaseTransfer[]>([]);
  const [options, setOptions] = useState<CaseTransferOption[]>([]);
  const [targetId, setTargetId] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canRequest = !terminalStatuses.has(dentalCase.status) && user.clinic_roles.some(
    (assignment) => assignment.clinic_id === dentalCase.clinic_id
      && ["clinic_manager", "managing_dentist"].includes(assignment.role),
  );
  const pending = transfers.find((item) => item.status === "pending");
  const pendingForUser = pending?.to_dentist_user_id === user.id ? pending : null;

  const load = useCallback(async () => {
    try {
      const [transferResult, optionResult] = await Promise.all([
        getCaseTransfers(dentalCase.id),
        canRequest
          ? getCaseTransferOptions(dentalCase.id)
          : Promise.resolve({ items: [] as CaseTransferOption[] }),
      ]);
      setTransfers(transferResult.items);
      setOptions(optionResult.items);
      setTargetId((current) => current || optionResult.items[0]?.id || "");
      setError(null);
    } catch {
      setError("Devir bilgileri yüklenemedi.");
    }
  }, [canRequest, dentalCase.id]);

  useEffect(() => {
    // Load the transfer resource when the selected case changes.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!targetId || reason.trim().length < 3) return;
    setBusy(true);
    try {
      await requestCaseTransfer(dentalCase.id, targetId, reason.trim());
      setReason("");
      await load();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  async function decide(transfer: CaseTransfer, accepted: boolean) {
    const decisionReason = accepted
      ? null
      : window.prompt("Devir talebini neden reddediyorsunuz? (en az 3 karakter)")?.trim();
    if (!accepted && (!decisionReason || decisionReason.length < 3)) return;
    if (accepted && !window.confirm("Vakanın sorumluluğunu devralmak istiyor musunuz?")) return;
    setBusy(true);
    try {
      await decideCaseTransfer(
        dentalCase.id,
        transfer.id,
        accepted ? "accepted" : "rejected",
        decisionReason || null,
      );
      await load();
      onChanged();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="case-panel transfer-panel">
      <p className="card-label">VAKA DEVRİ</p>
      <h2>Sorumlu hekim değişikliği</h2>
      <p className="panel-description">
        Devir, hedef hekimin kabulünden sonra geçerli olur. Eski kayıtlar korunur.
      </p>

      {error && <div className="form-error" role="alert">{error}</div>}
      {pendingForUser && (
        <div className="transfer-decision">
          <strong>{pendingForUser.from_dentist_name} → sizin adınıza</strong>
          <p>{pendingForUser.request_reason}</p>
          <div className="inline-actions">
            <button className="primary-button compact-button" disabled={busy} onClick={() => void decide(pendingForUser, true)}>Kabul et</button>
            <button className="secondary-button compact-button" disabled={busy} onClick={() => void decide(pendingForUser, false)}>Reddet</button>
          </div>
        </div>
      )}

      {canRequest && !pending && options.length > 0 && (
        <form className="transfer-form" onSubmit={(event) => void submit(event)}>
          <label>Yeni sorumlu hekim
            <select value={targetId} disabled={busy} onChange={(event) => setTargetId(event.target.value)}>
              {options.map((option) => <option key={option.id} value={option.id}>{option.full_name}</option>)}
            </select>
          </label>
          <label>Devir gerekçesi
            <textarea value={reason} minLength={3} maxLength={2000} rows={3} disabled={busy} onChange={(event) => setReason(event.target.value)} />
          </label>
          <button className="secondary-button" type="submit" disabled={busy || !targetId || reason.trim().length < 3}>Devir talebi gönder</button>
        </form>
      )}

      {pending && !pendingForUser && (
        <p className="transfer-pending">{pending.to_dentist_name} kullanıcısının kararı bekleniyor.</p>
      )}
      {transfers.length > 0 && (
        <div className="transfer-history">
          {transfers.map((item) => (
            <article key={item.id}>
              <strong>{item.from_dentist_name} → {item.to_dentist_name}</strong>
              <span className={`transfer-status ${item.status}`}>
                {item.status === "pending" ? "Bekliyor" : item.status === "accepted" ? "Kabul edildi" : "Reddedildi"}
              </span>
              <small>{formatDate(item.requested_at)} · {item.requested_by_name}</small>
              <p>{item.request_reason}</p>
              {item.decision_reason && <p><b>Karar:</b> {item.decision_reason}</p>}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
