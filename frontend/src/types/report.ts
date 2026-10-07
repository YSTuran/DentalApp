import type { CaseStatus } from "./case";

export interface ReportTotals {
  total: number;
  active: number;
  completed: number;
  closed: number;
  returned: number;
  reproductions: number;
  overdue: number;
  average_completion_hours: number | null;
}

export interface ReportCount {
  key: string;
  label: string;
  count: number;
}

export interface ReportClinic {
  id: string;
  name: string;
  count: number;
}

export interface ReportDentist {
  id: string;
  full_name: string;
  count: number;
}

export interface ReportStageDuration {
  status: CaseStatus;
  average_hours: number;
  sample_size: number;
}

export interface CaseReport {
  date_from: string | null;
  date_to: string | null;
  clinic_id: string | null;
  generated_at: string;
  totals: ReportTotals;
  status_counts: ReportCount[];
  clinic_counts: ReportClinic[];
  dentist_counts: ReportDentist[];
  stage_durations: ReportStageDuration[];
  available_clinics: ReportClinic[];
}
