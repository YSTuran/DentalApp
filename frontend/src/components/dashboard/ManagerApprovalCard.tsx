import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { listCases } from "../../lib/cases-api";

interface ApprovalCounts {
  managerReview: number;
  returnReview: number;
}

export function ManagerApprovalCard() {
  const [counts, setCounts] = useState<ApprovalCounts | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    void Promise.all([
      listCases({ status: "manager_review", limit: 1, offset: 0 }),
      listCases({ status: "return_review", limit: 1, offset: 0 }),
    ]).then(([managerCases, returnCases]) => {
      if (active) {
        setCounts({ managerReview: managerCases.total, returnReview: returnCases.total });
      }
    }).catch(() => {
      if (active) setError(true);
    });
    return () => { active = false; };
  }, []);

  return (
    <section className="info-card next-step-card">
      <p className="card-label">YÖNETİCİ HEKİM</p>
      <h2>Onay bekleyen vakalar</h2>
      {error ? (
        <p>Bekleyen vaka sayıları alınamadı. Güncel kuyruğu vaka listesinden görüntüleyebilirsiniz.</p>
      ) : counts === null ? (
        <p>Onay kuyruğu yükleniyor…</p>
      ) : (
        <dl>
          <div><dt>Tarama onayı</dt><dd>{counts.managerReview}</dd></div>
          <div><dt>İade kararı</dt><dd>{counts.returnReview}</dd></div>
        </dl>
      )}
      <div className="dashboard-management-links">
        <Link className="primary-link" to="/vakalar">Vaka kuyruğunu aç</Link>
      </div>
    </section>
  );
}
