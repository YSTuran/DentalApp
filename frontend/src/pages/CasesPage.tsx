import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { DemoBanner } from "../components/DemoBanner";
import { OperationsHeader } from "../components/OperationsHeader";
import { CaseStatusBadge } from "../components/cases/CaseStatusBadge";
import { caseStatusLabels, formatDate } from "../lib/case-format";
import { listCases } from "../lib/cases-api";
import type { CaseListResponse, CaseStatus } from "../types/case";

const pageSize = 20;
const createRoles = new Set(["managing_dentist", "dentist", "clinic_staff"]);
const labStatuses = new Set<CaseStatus>([
  "lab_design",
  "dentist_review",
  "design_revision_requested",
  "ready_for_production",
  "in_production",
  "production_completed",
  "shipped",
  "delivered",
  "return_review",
  "reproduction_requested",
]);

export function CasesPage() {
  const { user } = useAuth();
  const [data, setData] = useState<CaseListResponse | null>(null);
  const [status, setStatus] = useState<CaseStatus | "">("");
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await listCases({ status, search, limit: pageSize, offset }));
    } catch {
      setError("Vakalar yüklenemedi. API bağlantısını kontrol edip tekrar deneyin.");
    } finally {
      setLoading(false);
    }
  }, [offset, search, status]);

  useEffect(() => {
    // The request synchronizes this route with the current filters.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  const canCreate = user?.clinic_roles.some((item) => createRoles.has(item.role)) === true;
  const technicianOnly = user?.global_roles.includes("technician") === true
    && user.global_roles.includes("system_admin") === false
    && user.clinic_roles.length === 0;
  const statusOptions = (Object.entries(caseStatusLabels) as [CaseStatus, string][])
    .filter(([value]) => !technicianOnly || labStatuses.has(value));

  return (
    <div className="dashboard-shell">
      <DemoBanner />
      <OperationsHeader />
      <main className="management-content">
        <div className="page-heading">
          <div><p className="eyebrow">{technicianOnly ? "LABORATUVAR OPERASYONU" : "VAKA OPERASYONU"}</p><h1>{technicianOnly ? "Laboratuvar iş listesi" : "Vakalar"}</h1><p>{technicianOnly ? "Tasarım, hekim onayı ve üretim sırasındaki işleri takip edin." : "Rolünüze ve kliniğinize açık iş akışlarını takip edin."}</p></div>
          {canCreate && <Link className="primary-button link-button" to="/vakalar/yeni">Yeni vaka oluştur</Link>}
        </div>

        {error && <div className="form-error dashboard-error" role="alert">{error}</div>}
        <section className="management-card">
          <div className="filters-row case-filters">
            <form
              className="search-form"
              onSubmit={(event) => { event.preventDefault(); setOffset(0); setSearch(searchInput.trim()); }}
            >
              <input value={searchInput} onChange={(event) => setSearchInput(event.target.value)} placeholder="Vaka numarası veya hasta kodu" />
              <button className="secondary-button compact-button" type="submit">Ara</button>
            </form>
            <label className="filter-select">Durum
              <select value={status} onChange={(event) => { setStatus(event.target.value as CaseStatus | ""); setOffset(0); }}>
                <option value="">Tümü</option>
                {statusOptions.map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </label>
          </div>

          {loading ? <div className="table-state">Vakalar yükleniyor…</div> : data?.items.length === 0 ? (
            <div className="table-state"><div className="empty-state"><strong>{technicianOnly ? "Bekleyen laboratuvar işi yok." : "Bu görünümde vaka yok."}</strong><span>{technicianOnly ? "Yeni bir iş geldiğinde bu listede görünecektir." : "Filtreleri temizleyebilir veya yeni bir vaka oluşturabilirsiniz."}</span></div></div>
          ) : (
            <div className="table-scroll">
              <table className="data-table case-table">
                <thead><tr><th>Vaka</th><th>Hasta kodu</th><th>Klinik</th><th>Sorumlu hekim</th><th>Durum</th><th>Güncelleme</th><th /></tr></thead>
                <tbody>
                  {data?.items.map((item) => (
                    <tr key={item.id}>
                      <td><strong>{item.case_number}</strong><small>{item.patient_name ?? (technicianOnly ? "Hasta adı gizli" : "Hasta adı girilmedi")}</small></td>
                      <td><span className="code-chip">{item.patient_code ?? "—"}</span></td>
                      <td>{item.clinic_name}</td>
                      <td>{item.responsible_dentist_name}</td>
                      <td><CaseStatusBadge status={item.status} /></td>
                      <td>{formatDate(item.updated_at)}</td>
                      <td><Link className="primary-link" to={`/vakalar/${item.id}`}>İncele</Link></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {data && data.total > 0 && (
            <div className="pagination-row">
              <span>{data.total} kayıttan {data.offset + 1}–{Math.min(data.offset + data.items.length, data.total)}</span>
              <div>
                <button className="secondary-button" disabled={offset === 0 || loading} onClick={() => setOffset(Math.max(0, offset - pageSize))}>Önceki</button>
                <button className="secondary-button" disabled={offset + pageSize >= data.total || loading} onClick={() => setOffset(offset + pageSize)}>Sonraki</button>
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
