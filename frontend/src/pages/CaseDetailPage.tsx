import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { DemoBanner } from "../components/DemoBanner";
import { OperationsHeader } from "../components/OperationsHeader";
import { CaseFileList } from "../components/cases/CaseFileList";
import { CaseStatusBadge } from "../components/cases/CaseStatusBadge";
import { ManagerDecisionPanel } from "../components/cases/ManagerDecisionPanel";
import { StlUploadPanel } from "../components/cases/StlUploadPanel";
import { caseStatusLabels, formatDate } from "../lib/case-format";
import { getCase, getCaseHistory, submitCase } from "../lib/cases-api";
import type { CaseHistoryItem, DentalCase } from "../types/case";

const editableStatuses = new Set(["draft", "manager_revision_requested", "rescan_requested"]);
const StlViewerPanel = lazy(() => import("../components/cases/StlViewerPanel").then((module) => ({
  default: module.StlViewerPanel,
})));

export function CaseDetailPage() {
  const { caseId = "" } = useParams();
  const { user } = useAuth();
  const [dentalCase, setDentalCase] = useState<DentalCase | null>(null);
  const [history, setHistory] = useState<CaseHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const load = useCallback(async (quiet = false) => {
    if (!quiet) setLoading(true);
    try {
      const [caseResult, historyResult] = await Promise.all([getCase(caseId), getCaseHistory(caseId)]);
      setDentalCase(caseResult);
      setHistory(historyResult.items);
      setError(null);
    } catch {
      setError("Vaka bilgileri yüklenemedi veya bu vakaya erişim yetkiniz yok.");
    } finally {
      if (!quiet) setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    // The request synchronizes this route with the selected case.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  const validationPending = dentalCase?.file_versions.some((file) => file.mesh_status === "pending") === true;
  useEffect(() => {
    if (!validationPending) return;
    const timer = window.setInterval(() => void load(true), 3000);
    return () => window.clearInterval(timer);
  }, [load, validationPending]);

  const isOwner = useMemo(() => user !== null && dentalCase !== null && (
    dentalCase.created_by_user_id === user.id || dentalCase.responsible_dentist_user_id === user.id
  ), [dentalCase, user]);
  const canEdit = dentalCase !== null && isOwner && editableStatuses.has(dentalCase.status);
  const canManagerReview = dentalCase !== null
    && dentalCase.status === "manager_review"
    && user?.clinic_roles.some((assignment) => (
      assignment.clinic_id === dentalCase.clinic_id
      && assignment.role === "managing_dentist"
    )) === true;

  async function handleSubmit() {
    if (!dentalCase || !window.confirm("Vakayı yönetici hekim onayına göndermek istiyor musunuz? Bu aşamada form düzenlemeye kapanır.")) return;
    setSubmitting(true);
    setError(null);
    try {
      setDentalCase(await submitCase(dentalCase.id));
      setSuccess("Vaka yönetici hekim onayına gönderildi.");
      const result = await getCaseHistory(dentalCase.id);
      setHistory(result.items);
    } catch {
      setError("Vaka gönderilemedi. Zorunlu alanların dolu ve en son taramanın geçerli olduğundan emin olun.");
    } finally {
      setSubmitting(false);
    }
  }

  function handleManagerUpdated(updated: DentalCase, message: string) {
    setDentalCase(updated);
    setSuccess(message);
    setError(null);
    void getCaseHistory(updated.id).then((result) => setHistory(result.items));
  }

  return (
    <div className="dashboard-shell">
      <DemoBanner />
      <OperationsHeader />
      <main className="management-content">
        {loading ? <div className="table-state">Vaka yükleniyor…</div> : !dentalCase ? (
          <section className="state-page"><h1>Vaka açılamadı</h1><p>{error}</p><Link className="primary-link" to="/vakalar">Vakalara dön</Link></section>
        ) : (
          <>
            <div className="case-detail-heading">
              <div><Link className="text-link" to="/vakalar">← Vakalara dön</Link><p className="eyebrow">{dentalCase.clinic_name}</p><h1>{dentalCase.case_number}</h1><p>Son güncelleme {formatDate(dentalCase.updated_at)}</p></div>
              <div className="case-heading-actions"><CaseStatusBadge status={dentalCase.status} />{canEdit && <button className="primary-button" disabled={submitting || validationPending} onClick={() => void handleSubmit()}>{submitting ? "Gönderiliyor…" : "Yönetici onayına gönder"}</button>}</div>
            </div>
            {error && <div className="form-error dashboard-error" role="alert">{error}</div>}
            {success && <div className="success-message">{success}</div>}

            <div className="case-detail-grid">
              <div className="case-main-column">
                <section className="case-panel">
                  <div className="panel-heading"><div><p className="card-label">VAKA BİLGİLERİ</p><h2>Klinik talep</h2></div>{canEdit && <span className="edit-hint">Düzenleme ekranı sonraki dilimde eklenecek</span>}</div>
                  <dl className="case-facts">
                    <div><dt>Hasta kodu</dt><dd>{dentalCase.patient_code ?? "—"}</dd></div>
                    {dentalCase.patient_name !== undefined && <div><dt>Hasta adı</dt><dd>{dentalCase.patient_name ?? "—"}</dd></div>}
                    <div><dt>Sorumlu hekim</dt><dd>{dentalCase.responsible_dentist_name}</dd></div>
                    <div><dt>Aparey tipi</dt><dd>{dentalCase.details.appliance_type ?? "—"}</dd></div>
                    <div><dt>Malzeme</dt><dd>{dentalCase.details.material ?? "—"}</dd></div>
                    <div><dt>Diş numaraları</dt><dd>{dentalCase.details.tooth_numbers.join(", ") || "—"}</dd></div>
                    <div className="wide"><dt>Özel notlar</dt><dd>{dentalCase.details.special_notes ?? "—"}</dd></div>
                    {Object.entries(dentalCase.details.extra_fields).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{String(value)}</dd></div>)}
                  </dl>
                </section>
                <Suspense fallback={<section className="case-panel viewer-module-loading">3D görüntüleyici yükleniyor…</section>}>
                  <StlViewerPanel
                    key={dentalCase.file_versions.map((file) => file.id).join(":")}
                    caseId={dentalCase.id}
                    files={dentalCase.file_versions}
                  />
                </Suspense>
                <CaseFileList caseId={dentalCase.id} caseNumber={dentalCase.case_number} files={dentalCase.file_versions} />
                {canEdit && user && <StlUploadPanel caseId={dentalCase.id} userId={user.id} onCompleted={() => void load(true)} />}
              </div>

              <aside className="case-side-column">
                {canManagerReview && user && (
                  <ManagerDecisionPanel
                    dentalCase={dentalCase}
                    user={user}
                    onUpdated={handleManagerUpdated}
                  />
                )}
                <section className="case-panel"><p className="card-label">İŞ AKIŞI</p><h2>{caseStatusLabels[dentalCase.status]}</h2><p className="panel-description">İki onay tamamlanmadan vaka üretim kuyruğuna alınamaz.</p></section>
                {dentalCase.approvals.length > 0 && (
                  <section className="case-panel">
                    <p className="card-label">DEĞİŞMEZ KARARLAR</p>
                    <div className="approval-list">
                      {[...dentalCase.approvals].reverse().map((approval) => (
                        <article key={approval.id}>
                          <strong>{approval.decision === "approved" ? "Onaylandı" : approval.decision === "revision_requested" ? "Düzeltme istendi" : "Reddedildi"}</strong>
                          <span>{approval.approval_type === "manager_scan" ? "Yönetici tarama kararı" : "Hekim tasarım kararı"}</span>
                          <small>{formatDate(approval.created_at)}</small>
                          {approval.is_self_approval && <em>Yönetici kendi vakasını onayladı</em>}
                          {approval.reason && <p>{approval.reason}</p>}
                        </article>
                      ))}
                    </div>
                  </section>
                )}
                <section className="case-panel"><div className="panel-heading"><div><p className="card-label">GEÇMİŞ</p><h2>İşlem zaman çizelgesi</h2></div></div>
                  <ol className="case-timeline">
                    {[...history].reverse().map((item) => <li key={item.id}><i aria-hidden="true" /><div><strong>{caseStatusLabels[item.to_status]}</strong><span>{item.action}</span><small>{formatDate(item.created_at)}</small>{item.reason && <p>{item.reason}</p>}</div></li>)}
                  </ol>
                </section>
              </aside>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
