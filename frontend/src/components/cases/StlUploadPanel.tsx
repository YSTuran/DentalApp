import { useRef, useState } from "react";

import { useResumableUpload } from "../../hooks/useResumableUpload";
import { formatBytes } from "../../lib/case-format";

interface Props {
  caseId: string;
  userId: string;
  onCompleted: () => void;
}

export function StlUploadPanel({ caseId, userId, onCompleted }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const { phase, progress, error, upload, pause } = useResumableUpload(userId);
  const busy = ["preparing", "uploading", "finalizing"].includes(phase);

  async function handleUpload() {
    if (!file) return;
    const result = await upload(caseId, file);
    if (result) {
      setFile(null);
      if (inputRef.current) inputRef.current.value = "";
      onCompleted();
    }
  }

  return (
    <section className="case-panel upload-panel">
      <div className="panel-heading">
        <div><p className="card-label">STL TARAMA</p><h2>Tarama dosyası yükle</h2></div>
        <span className="upload-capacity">200 MB+ destekli</span>
      </div>
      <p className="panel-description">
        Yükleme parçalara ayrılır. Bağlantı kesilirse aynı dosyayı yeniden seçerek devam edebilirsiniz.
      </p>
      <input
        ref={inputRef}
        className="file-input"
        type="file"
        accept=".stl,model/stl"
        disabled={busy}
        onChange={(event) => setFile(event.target.files?.[0] ?? null)}
      />
      {file && <p className="selected-file"><strong>{file.name}</strong><span>{formatBytes(file.size)}</span></p>}
      {phase !== "idle" && (
        <div className="upload-progress" aria-live="polite">
          <div><span style={{ width: `${progress}%` }} /></div>
          <p>{phase === "finalizing" ? "Dosya tamamlanıyor…" : `%${progress} yüklendi`}</p>
        </div>
      )}
      {error && <div className="form-error" role="alert">{error}</div>}
      <div className="form-actions">
        <button className="primary-button" type="button" disabled={!file || busy} onClick={() => void handleUpload()}>
          {phase === "paused" || phase === "error" ? "Yüklemeye devam et" : "STL yükle"}
        </button>
        {phase === "uploading" && <button className="secondary-button" type="button" onClick={pause}>Duraklat</button>}
      </div>
    </section>
  );
}
