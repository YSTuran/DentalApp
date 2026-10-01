import { apiBlobRequest, apiRequest, csrfRequest } from "./api";
import type {
  CaseCreateOptions,
  CaseHistoryItem,
  CaseListResponse,
  CaseStatus,
  CaseWritePayload,
  DentalCase,
  UploadCompleteResponse,
  UploadSession,
} from "../types/case";

interface CaseListFilters {
  status?: CaseStatus | "";
  search?: string;
  limit?: number;
  offset?: number;
}

function queryString(values: Record<string, string | number | undefined>): string {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== "") params.set(key, String(value));
  });
  const query = params.toString();
  return query ? `?${query}` : "";
}

export function listCases(filters: CaseListFilters = {}): Promise<CaseListResponse> {
  return apiRequest(`/api/cases${queryString({ ...filters })}`);
}

export function getCase(caseId: string): Promise<DentalCase> {
  return apiRequest(`/api/cases/${caseId}`);
}

export function getCaseHistory(caseId: string): Promise<{ items: CaseHistoryItem[] }> {
  return apiRequest(`/api/cases/${caseId}/history`);
}

export function getCaseCreateOptions(): Promise<CaseCreateOptions> {
  return apiRequest("/api/cases/create-options");
}

export function createCase(payload: CaseWritePayload): Promise<DentalCase> {
  return csrfRequest("/api/cases", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function updateCase(
  caseId: string,
  payload: Omit<CaseWritePayload, "clinic_id">,
): Promise<DentalCase> {
  return csrfRequest(`/api/cases/${caseId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function submitCase(caseId: string): Promise<DentalCase> {
  return csrfRequest(`/api/cases/${caseId}/submit`, { method: "POST" });
}

export function startUpload(caseId: string, file: File): Promise<UploadSession> {
  return csrfRequest(`/api/cases/${caseId}/uploads`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      kind: "scan",
      original_filename: file.name,
      expected_size: file.size,
    }),
  });
}

export function getUpload(caseId: string, uploadId: string): Promise<UploadSession> {
  return apiRequest(`/api/cases/${caseId}/uploads/${uploadId}`);
}

export function sendUploadChunk(
  caseId: string,
  uploadId: string,
  offset: number,
  chunk: Blob,
  signal: AbortSignal,
): Promise<UploadSession> {
  return csrfRequest(`/api/cases/${caseId}/uploads/${uploadId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/offset+octet-stream",
      "Upload-Offset": String(offset),
    },
    body: chunk,
    signal,
  });
}

export function completeUpload(caseId: string, uploadId: string): Promise<UploadCompleteResponse> {
  return csrfRequest(`/api/cases/${caseId}/uploads/${uploadId}/complete`, { method: "POST" });
}

export async function downloadCaseFile(
  caseId: string,
  fileId: string,
  filename: string,
): Promise<void> {
  const blob = await apiBlobRequest(`/api/cases/${caseId}/files/${fileId}`);
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
