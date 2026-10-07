import { useCallback, useRef, useState } from "react";

import { completeUpload, getUpload, sendUploadChunk, startUpload } from "../lib/cases-api";
import type { CaseFileKind, UploadCompleteResponse, UploadSession } from "../types/case";

type UploadPhase = "idle" | "preparing" | "uploading" | "paused" | "finalizing" | "completed" | "error";

interface SavedUpload {
  uploadId: string;
  fingerprint: string;
}

function storageKey(userId: string, caseId: string, kind: CaseFileKind): string {
  return `dentalapp:${kind}-upload:${userId}:${caseId}`;
}

function readSaved(key: string): SavedUpload | null {
  try {
    const value = localStorage.getItem(key);
    return value ? JSON.parse(value) as SavedUpload : null;
  } catch {
    return null;
  }
}

function saveUpload(key: string, upload: SavedUpload): void {
  try {
    localStorage.setItem(key, JSON.stringify(upload));
  } catch {
    // Server offset remains authoritative when browser storage is unavailable.
  }
}

function clearSaved(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch {
    // Nothing else is required when browser storage is unavailable.
  }
}

function hashFile(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const worker = new Worker(new URL("../workers/file-hash.worker.ts", import.meta.url), {
      type: "module",
    });
    worker.addEventListener("message", (event: MessageEvent<{ digest?: string; error?: string }>) => {
      worker.terminate();
      if (event.data.digest) {
        resolve(event.data.digest);
      } else {
        reject(new Error(event.data.error ?? "Dosya özeti hesaplanamadı."));
      }
    });
    worker.addEventListener("error", () => {
      worker.terminate();
      reject(new Error("Dosya özeti hesaplanamadı."));
    });
    worker.postMessage(file);
  });
}

export function useResumableUpload(userId: string, kind: CaseFileKind = "scan") {
  const controller = useRef<AbortController | null>(null);
  const [phase, setPhase] = useState<UploadPhase>("idle");
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const pause = useCallback(() => {
    controller.current?.abort();
  }, []);

  const upload = useCallback(async (
    caseId: string,
    file: File,
  ): Promise<UploadCompleteResponse | null> => {
    if (!file.name.toLocaleLowerCase("tr-TR").endsWith(".stl") || file.size === 0) {
      setPhase("error");
      setError("Lütfen içeriği bulunan bir STL dosyası seçin.");
      return null;
    }

    setError(null);
    setPhase("preparing");
    const key = storageKey(userId, caseId, kind);
    try {
      const fingerprint = await hashFile(file);
      let session: UploadSession | null = null;
      const saved = readSaved(key);

      if (saved?.fingerprint === fingerprint) {
        try {
          const existing = await getUpload(caseId, saved.uploadId);
          if (
            ["pending", "uploading"].includes(existing.status)
            && existing.expected_size === file.size
            && existing.expected_sha256 === fingerprint
            && new Date(existing.expires_at).getTime() > Date.now()
          ) {
            session = existing;
          }
        } catch {
          clearSaved(key);
        }
      } else if (saved) {
        clearSaved(key);
      }

      if (session === null) {
        session = await startUpload(caseId, file, kind, fingerprint);
        saveUpload(key, { uploadId: session.id, fingerprint });
      }

      controller.current = new AbortController();
      setPhase("uploading");
      let offset = session.received_size;
      setProgress(Math.round((offset / file.size) * 100));

      while (offset < file.size) {
        const end = Math.min(offset + session.chunk_max_bytes, file.size);
        session = await sendUploadChunk(
          caseId,
          session.id,
          offset,
          file.slice(offset, end),
          controller.current.signal,
        );
        offset = session.received_size;
        setProgress(Math.round((offset / file.size) * 100));
      }

      setPhase("finalizing");
      const completed = await completeUpload(caseId, session.id);
      clearSaved(key);
      setProgress(100);
      setPhase("completed");
      return completed;
    } catch (caught) {
      if (caught instanceof DOMException && caught.name === "AbortError") {
        setPhase("paused");
        return null;
      }
      setPhase("error");
      setError("Dosya hazırlanamadı veya yükleme kesildi. Aynı dosyayı seçerek tekrar deneyin.");
      return null;
    } finally {
      controller.current = null;
    }
  }, [kind, userId]);

  return { phase, progress, error, upload, pause };
}
