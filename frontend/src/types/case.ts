export type CaseStatus =
  | "draft"
  | "manager_review"
  | "manager_revision_requested"
  | "manager_rejected"
  | "lab_design"
  | "dentist_review"
  | "design_revision_requested"
  | "ready_for_production"
  | "in_production"
  | "production_completed"
  | "shipped"
  | "delivered"
  | "return_review"
  | "reproduction_requested"
  | "rescan_requested"
  | "cancelled";

export type CaseFileKind = "scan" | "design";
export type MeshStatus = "pending" | "valid" | "invalid" | "failed";
export type UploadStatus = "pending" | "uploading" | "completed" | "failed" | "expired";

export interface CaseDetails {
  appliance_type: string | null;
  material: string | null;
  tooth_numbers: string[];
  special_notes: string | null;
  extra_fields: Record<string, unknown>;
}

export interface CaseFileVersion {
  id: string;
  kind: CaseFileKind;
  version_number: number;
  original_filename?: string;
  size_bytes: number;
  mesh_status: MeshStatus;
  mesh_report: Record<string, unknown> | null;
  is_locked: boolean;
  mesh_validation_attempts: number;
  mesh_validated_at: string | null;
  uploaded_by_user_id: string;
  created_at: string;
}

export interface DentalCase {
  id: string;
  case_number: string;
  clinic_id: string;
  clinic_name: string;
  created_by_user_id: string;
  responsible_dentist_user_id: string;
  responsible_dentist_name: string;
  patient_code: string | null;
  patient_name?: string;
  status: CaseStatus;
  submitted_at: string | null;
  cancelled_at: string | null;
  created_at: string;
  updated_at: string;
  details: CaseDetails;
  file_versions: CaseFileVersion[];
}

export interface CaseListResponse {
  items: DentalCase[];
  total: number;
  limit: number;
  offset: number;
}

export interface CaseHistoryItem {
  id: string;
  from_status: CaseStatus | null;
  to_status: CaseStatus;
  action: string;
  actor_user_id: string;
  reason: string | null;
  created_at: string;
}

export interface DentistOption {
  id: string;
  full_name: string;
}

export interface ClinicCaseOption {
  id: string;
  code: string;
  name: string;
  dentists: DentistOption[];
}

export interface CaseCreateOptions {
  clinics: ClinicCaseOption[];
}

export interface CaseWritePayload {
  clinic_id: string;
  responsible_dentist_user_id: string;
  patient_code: string | null;
  patient_name: string | null;
  appliance_type: string | null;
  material: string | null;
  tooth_numbers: string[];
  special_notes: string | null;
  extra_fields: Record<string, string>;
  reason?: string | null;
}

export interface UploadSession {
  id: string;
  case_id: string;
  kind: CaseFileKind;
  original_filename: string;
  expected_size: number;
  received_size: number;
  expected_sha256: string | null;
  status: UploadStatus;
  expires_at: string;
  failure_reason: string | null;
  completed_file_version_id: string | null;
  chunk_max_bytes: number;
}

export interface UploadCompleteResponse {
  upload: UploadSession;
  file_version: CaseFileVersion;
  validation_queued: boolean;
}
