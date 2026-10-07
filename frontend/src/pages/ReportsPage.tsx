import { useCallback, useEffect, useMemo, useState } from "react";

import { useAuth } from "../auth/AuthContext";
import { CaseReportDocument } from "../components/reports/CaseReportDocument";
import { DemoBanner } from "../components/DemoBanner";
import { OperationsHeader } from "../components/OperationsHeader";
import { PrintPortal } from "../components/printing/PrintPortal";
import { usePrintDocument } from "../hooks/usePrintDocument";
import { caseStatusLabels } from "../lib/case-format";
import { getCaseReport } from "../lib/reports-api";
import type { CaseReport } from "../types/report";

function metricHours(value: number | null): string {
  return value === null ? "—" : `${value.toLocaleString("tr-TR")} sa`;
}

export function ReportsPage() {
  const { user } = useAuth();
  const [clinicOverride, setClinicOverride] = useState<string | null>(null);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [report, setReport] = useState<CaseReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { isPrinting, print } = usePrintDocument();

  const clinicId = clinicOverride ?? user?.preferences.active_clinic_id ?? "";
  const load = useCallback(async (signal: AbortSignal) => {
    setLoading(true);
    try {
      setReport(await getCaseReport({
        dateFrom: dateFrom || undefined,
        dateTo: dateTo || undefined,
        clinicId: clinicId || undefined,
      }, signal));
      setError(null);
    } catch (caught) {
      if (!signal.aborted) {
        setError(caught instanceof Error ? caught.message : "Rapor yüklenemedi.");
      }
    } finally {
      if (!signal.aborted) setLoading(false);
    }
  }, [clinicId, dateFrom, dateTo]);

  useEffect(() => {
    const controller = new AbortController();
    // Report data follows the currently selected filters.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const largestStatus = useMemo(
    () => Math.max(1, ...(report?.status_counts.map((item) => item.count) ?? [])),
    [report],
  );

  return (
    <div className="dashboard-shell">
      <DemoBanner />
      <OperationsHeader />
      <main className="management-content">
        <div className="page-heading">
          <div><p className="eyebrow">OPERASYON ANALİZİ</p><h1>Raporlar</h1><p>Yetkiniz kapsamındaki vaka, iş yükü ve bekleme sürelerini inceleyin.</p></div>
          <button className="secondary-button" disabled={!report || loading} onClick={print}>PDF olarak yazdır</button>
        </div>

        <section className="report-filters">
          <label>Klinik<select value={clinicId} onChange={(event) => setClinicOverride(event.target.value)}><option value="">Yetkili tüm klinikler</option>{report?.available_clinics.map((clinic) => <option key={clinic.id} value={clinic.id}>{clinic.name}</option>)}</select></label>
          <label>Başlangıç<input type="date" value={dateFrom} max={dateTo || undefined} onChange={(event) => setDateFrom(event.target.value)} /></label>
          <label>Bitiş<input type="date" value={dateTo} min={dateFrom || undefined} onChange={(event) => setDateTo(event.target.value)} /></label>
        </section>

        {error && <div className="form-error" role="alert">{error}</div>}
        {loading ? <div className="table-state">Rapor hazırlanıyor…</div> : report && (
          <>
            <section className="report-metrics">
              <article><span>Toplam vaka</span><strong>{report.totals.total}</strong></article>
              <article><span>Aktif</span><strong>{report.totals.active}</strong></article>
              <article><span>Tamamlanan</span><strong>{report.totals.completed}</strong></article>
              <article><span>İade</span><strong>{report.totals.returned}</strong></article>
              <article><span>Yeniden üretim</span><strong>{report.totals.reproductions}</strong></article>
              <article className={report.totals.overdue > 0 ? "warning" : ""}><span>Geciken</span><strong>{report.totals.overdue}</strong></article>
              <article><span>Ort. tamamlanma</span><strong>{metricHours(report.totals.average_completion_hours)}</strong></article>
            </section>

            <div className="report-grid">
              <section className="report-card"><h2>Durum dağılımı</h2>{report.status_counts.length === 0 ? <p>Bu filtrelerde vaka yok.</p> : <div className="report-bars">{report.status_counts.map((item) => <div key={item.key}><span>{item.label}</span><i><b style={{ width: `${(item.count / largestStatus) * 100}%` }} /></i><strong>{item.count}</strong></div>)}</div>}</section>
              <section className="report-card"><h2>Hekim iş yükü</h2><div className="report-ranking">{report.dentist_counts.map((item) => <div key={item.id}><span>{item.full_name}</span><strong>{item.count} vaka</strong></div>)}</div></section>
              <section className="report-card"><h2>Ortalama aşama süreleri</h2><div className="report-ranking">{report.stage_durations.map((item) => <div key={item.status}><span>{caseStatusLabels[item.status]}</span><strong>{metricHours(item.average_hours)} · {item.sample_size} örnek</strong></div>)}</div></section>
              <section className="report-card"><h2>Klinik dağılımı</h2><div className="report-ranking">{report.clinic_counts.map((item) => <div key={item.id}><span>{item.name}</span><strong>{item.count} vaka</strong></div>)}</div></section>
            </div>
          </>
        )}
      </main>
      {isPrinting && report && <PrintPortal><CaseReportDocument report={report} /></PrintPortal>}
    </div>
  );
}
