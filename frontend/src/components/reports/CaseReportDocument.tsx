import { caseStatusLabels, formatDate } from "../../lib/case-format";
import type { CaseReport } from "../../types/report";

interface Props {
  report: CaseReport;
}

function hours(value: number | null): string {
  return value === null ? "—" : `${value.toLocaleString("tr-TR")} saat`;
}

export function CaseReportDocument({ report }: Props) {
  const clinic = report.available_clinics.find((item) => item.id === report.clinic_id)?.name;
  return (
    <article className="case-report-document">
      <header>
        <div><span>DENTALAPP</span><h1>Vaka operasyon raporu</h1></div>
        <dl>
          <div><dt>Oluşturulma</dt><dd>{formatDate(report.generated_at)}</dd></div>
          <div><dt>Klinik</dt><dd>{clinic ?? "Yetkili tüm klinikler"}</dd></div>
          <div><dt>Tarih aralığı</dt><dd>{report.date_from ?? "İlk kayıt"} – {report.date_to ?? "Bugün"}</dd></div>
        </dl>
      </header>

      <section className="report-print-summary">
        <div><span>Toplam vaka</span><strong>{report.totals.total}</strong></div>
        <div><span>Aktif</span><strong>{report.totals.active}</strong></div>
        <div><span>Tamamlanan</span><strong>{report.totals.completed}</strong></div>
        <div><span>İade</span><strong>{report.totals.returned}</strong></div>
        <div><span>Geciken</span><strong>{report.totals.overdue}</strong></div>
        <div><span>Ort. tamamlanma</span><strong>{hours(report.totals.average_completion_hours)}</strong></div>
      </section>

      <div className="report-print-grid">
        <section><h2>Durum dağılımı</h2><table><tbody>{report.status_counts.map((item) => <tr key={item.key}><th>{item.label}</th><td>{item.count}</td></tr>)}</tbody></table></section>
        <section><h2>Hekim iş yükü</h2><table><tbody>{report.dentist_counts.map((item) => <tr key={item.id}><th>{item.full_name}</th><td>{item.count}</td></tr>)}</tbody></table></section>
        <section><h2>Aşama süreleri</h2><table><tbody>{report.stage_durations.map((item) => <tr key={item.status}><th>{caseStatusLabels[item.status]}</th><td>{hours(item.average_hours)} ({item.sample_size})</td></tr>)}</tbody></table></section>
        <section><h2>Klinik dağılımı</h2><table><tbody>{report.clinic_counts.map((item) => <tr key={item.id}><th>{item.name}</th><td>{item.count}</td></tr>)}</tbody></table></section>
      </div>
      <footer>Rapor toplulaştırılmış verilerden oluşturulmuştur; hasta adı ve hasta kodu içermez.</footer>
    </article>
  );
}
