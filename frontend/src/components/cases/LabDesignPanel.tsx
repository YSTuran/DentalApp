import { useRef, useState } from "react";

import { useResumableUpload } from "../../hooks/useResumableUpload";
import { ApiError } from "../../lib/api";
import { latestCaseFile } from "../../lib/case-files";
import { formatBytes } from "../../lib/case-format";
import { submitDesign } from "../../lib/cases-api";
import type { DentalCase } from "../../types/case";
import { MeshStatusBadge } from "./CaseStatusBadge";

interface Props {
  dentalCase: DentalCase;
  userId: string;
  onRefresh: () => void;
  onUpdated: (updated: DentalCase, message: string) => void;
}

export function LabDesignPanel({ dentalCase, userId, onRefresh, onUpdated }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const { phase, progress, error, upload, pause } = useResumableUpload(userId, "design");
  const latestDesign = latestCaseFile(dentalCase.file_versions, "design");
  const busy = ["preparing", "uploading", "finalizing"].includes(phase);

  async function handleUpload() {
    if (!file) return;
    const result = await upload(dentalCase.id, file);
    if (!result) return;
    setFile(null);
    if (inputRef.current) inputRef.current.value = "";
    setSubmitError(null);
    onRefresh();
  }

  async function handleSubmit() {
    if (!latestDesign || latestDesign.mesh_status !== "valid") return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const updated = await submitDesign(dentalCase.id, latestDesign.id);
      onUpdated(updated, "Tasarım sorumlu hekimin onayına gönderildi.");
    } catch (caught) {
      if (caught instanceof ApiError && caught.detail === "case_design_revision_required") {
        setSubmitError("Düzeltme talebi için yeni bir tasarım sürümü yüklemelisiniz.");
      } else if (caught instanceof ApiError && caught.detail === "case_design_version_changed") {
        setSubmitError("Tasarım sürümü değişti. Vakayı yenileyip en son sürümü kontrol edin.");
      } else {
        setSubmitError("Tasarım gönderilemedi. Mesh sonucunu ve vaka durumunu kontrol edin.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="case-panel lab-design-panel">
      <div className="panel-heading"><div><p className="card-label">LABORATUVAR TASARIMI</p><h2>Tasarım STL süreci</h2></div><span className="upload-capacity">Sürümlü</span></div>
      <p className="panel-description">Tasarımı yükleyin, mesh doğrulamasını bekleyin ve yalnızca geçerli son sürümü hekime gönderin.</p>
      {dentalCase.status === "design_revision_requested" && <div className="workflow-notice">Hekim düzeltme istedi. Eski sürüm korunacak; yeni bir tasarım sürümü yükleyin.</div>}
      <input ref={inputRef} className="file-input" type="file" accept=".stl,model/stl" disabled={busy || submitting} onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
      {file && <p className="selected-file"><strong>{file.name}</strong><span>{formatBytes(file.size)}</span></p>}
      {phase !== "idle" && <div className="upload-progress" aria-live="polite"><div><span style={{ width: `${progress}%` }} /></div><p>{phase === "finalizing" ? "Dosya tamamlanıyor…" : `%${progress} yüklendi`}</p></div>}
      {error && <div className="form-error" role="alert">{error}</div>}
      <div className="form-actions lab-upload-actions"><button className="secondary-button" type="button" disabled={!file || busy || submitting} onClick={() => void handleUpload()}>{phase === "paused" || phase === "error" ? "Yüklemeye devam et" : "Tasarım STL yükle"}</button>{phase === "uploading" && <button className="secondary-button" type="button" onClick={pause}>Duraklat</button>}</div>
      {latestDesign && <div className="design-submit-row"><div><strong>Tasarım v{latestDesign.version_number}</strong><span>{formatBytes(latestDesign.size_bytes)}</span></div><MeshStatusBadge status={latestDesign.mesh_status} /><button className="primary-button compact-button" type="button" disabled={submitting || busy || latestDesign.mesh_status !== "valid"} onClick={() => void handleSubmit()}>{submitting ? "Gönderiliyor…" : "Hekim onayına gönder"}</button></div>}
      {submitError && <div className="form-error" role="alert">{submitError}</div>}
    </section>
  );
}
