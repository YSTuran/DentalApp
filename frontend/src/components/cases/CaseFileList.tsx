import { useState } from "react";

import { downloadCaseFile } from "../../lib/cases-api";
import { formatBytes, formatDate } from "../../lib/case-format";
import { hasMeshWarnings } from "../../lib/mesh-report";
import type { CaseFileVersion } from "../../types/case";
import { MeshStatusBadge } from "./CaseStatusBadge";

interface Props {
  caseId: string;
  caseNumber: string;
  files: CaseFileVersion[];
}

export function CaseFileList({ caseId, caseNumber, files }: Props) {
  const [downloading, setDownloading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function download(file: CaseFileVersion) {
    setDownloading(file.id);
    setError(null);
    try {
      await downloadCaseFile(caseId, file.id, `${caseNumber}-${file.kind}-v${file.version_number}.stl`);
    } catch {
      setError("Dosya indirilemedi. Dosya depolamasını ve API bağlantısını kontrol edin.");
    } finally {
      setDownloading(null);
    }
  }

  return (
    <section className="case-panel">
      <div className="panel-heading"><div><p className="card-label">DOSYALAR</p><h2>Sürüm geçmişi</h2></div></div>
      {files.length === 0 ? (
        <p className="empty-note">Henüz STL dosyası yüklenmedi.</p>
      ) : (
        <div className="file-version-list">
          {[...files].reverse().map((file) => (
            <article key={file.id}>
              <div className="file-icon" aria-hidden="true">STL</div>
              <div className="file-main">
                <strong>{file.kind === "scan" ? "Ağız içi tarama" : "Laboratuvar tasarımı"} · v{file.version_number}</strong>
                <span>{file.original_filename ?? "Gizli dosya adı"} · {formatBytes(file.size_bytes)}</span>
                <small>{formatDate(file.created_at)}{file.is_locked ? " · Kilitli" : ""}</small>
              </div>
              <MeshStatusBadge status={file.mesh_status} hasWarnings={hasMeshWarnings(file.mesh_report)} />
              <button className="secondary-button compact-button" disabled={downloading === file.id} onClick={() => void download(file)}>
                {downloading === file.id ? "İndiriliyor…" : "İndir"}
              </button>
            </article>
          ))}
        </div>
      )}
      {error && <div className="form-error file-error" role="alert">{error}</div>}
    </section>
  );
}
