import { useCallback, useEffect, useRef, useState } from "react";

import { completeUpload, getUpload, sendUploadChunk, startUpload } from "../lib/cases-api";
import { ApiError } from "../lib/api";
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

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

function uploadErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.detail === "case_upload_session_limit_reached") {
      return "Çok fazla etkin yükleme var. Bir yüklemeyi tamamlayın veya süresinin dolmasını bekleyin.";
    }
    if (error.detail === "case_upload_quota_exceeded") {
      return "Etkin yüklemeler için ayrılan geçici depolama kotası doldu.";
    }
    if (error.detail === "case_file_too_large") {
      return "Seçilen STL dosyası sunucunun dosya boyutu sınırını aşıyor.";
    }
  }
  return "Dosya hazırlanamadı veya yükleme kesildi. Aynı dosyayı seçerek tekrar deneyin.";
}

function hashFile(file: File, signal: AbortSignal): Promise<string> {
  return new Promise((resolve, reject) => {
    const worker = new Worker(new URL("../workers/file-hash.worker.ts", import.meta.url), {
      type: "module",
    });

    const cleanup = () => {
      signal.removeEventListener("abort", handleAbort);
      worker.terminate();
    };
    const handleAbort = () => {
      cleanup();
      reject(new DOMException("Dosya hazırlama iptal edildi.", "AbortError"));
    };
    const handleMessage = (event: MessageEvent<{ digest?: string; error?: string }>) => {
      cleanup();
      if (event.data.digest) {
        resolve(event.data.digest);
      } else {
        reject(new Error(event.data.error ?? "Dosya özeti hesaplanamadı."));
      }
    };
    const handleError = () => {
      cleanup();
      reject(new Error("Dosya özeti hesaplanamadı."));
    };

    if (signal.aborted) {
      handleAbort();
      return;
    }
    signal.addEventListener("abort", handleAbort, { once: true });
    worker.addEventListener("message", handleMessage);
    worker.addEventListener("error", handleError);
    worker.postMessage(file);
  });
}

export function useResumableUpload(userId: string, kind: CaseFileKind = "scan") {
  const controller = useRef<AbortController | null>(null);
  const mounted = useRef(true);
  const [phase, setPhase] = useState<UploadPhase>("idle");
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const pause = useCallback(() => {
    controller.current?.abort();
  }, []);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      controller.current?.abort();
    };
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
    controller.current?.abort();
    const activeController = new AbortController();
    controller.current = activeController;
    try {
      const fingerprint = await hashFile(file, activeController.signal);
      let session: UploadSession | null = null;
      const saved = readSaved(key);

      if (saved?.fingerprint === fingerprint) {
        try {
          const existing = await getUpload(caseId, saved.uploadId, activeController.signal);
          if (
            ["pending", "uploading"].includes(existing.status)
            && existing.expected_size === file.size
            && existing.expected_sha256 === fingerprint
            && new Date(existing.expires_at).getTime() > Date.now()
          ) {
            session = existing;
          }
        } catch (caught) {
          if (isAbortError(caught)) throw caught;
          if (caught instanceof ApiError && caught.status === 404) {
            clearSaved(key);
          } else {
            throw caught;
          }
        }
      } else if (saved) {
        clearSaved(key);
      }

      if (session === null) {
        session = await startUpload(
          caseId,
          file,
          kind,
          fingerprint,
          activeController.signal,
        );
        saveUpload(key, { uploadId: session.id, fingerprint });
      }

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
          activeController.signal,
        );
        offset = session.received_size;
        setProgress(Math.round((offset / file.size) * 100));
      }

      setPhase("finalizing");
      const completed = await completeUpload(caseId, session.id, activeController.signal);
      clearSaved(key);
      setProgress(100);
      setPhase("completed");
      return completed;
    } catch (caught) {
      if (!mounted.current) return null;
      if (isAbortError(caught)) {
        if (controller.current === activeController) setPhase("paused");
        return null;
      }
      setPhase("error");
      setError(uploadErrorMessage(caught));
      return null;
    } finally {
      if (controller.current === activeController) controller.current = null;
    }
  }, [kind, userId]);

  return { phase, progress, error, upload, pause };
}
