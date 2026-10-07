export type ReturnReasonCode = "fit_issue" | "damaged" | "manufacturing_defect" | "other";
export type ReturnResolution = "reproduction" | "rescan";

export interface ProductionRun {
  id: string;
  case_id: string;
  attempt_number: number;
  design_file_version_id: string;
  work_order_number: string;
  started_by_user_id: string;
  notes: string | null;
  started_at: string;
}

export interface ProductionCompletion {
  id: string;
  production_run_id: string;
  material: string;
  lot_number: string;
  quantity: number;
  completed_by_user_id: string;
  notes: string | null;
  completed_at: string;
}

export interface Shipment {
  id: string;
  production_run_id: string;
  destination_clinic_id: string;
  carrier: string;
  tracking_number: string;
  shipped_by_user_id: string;
  notes: string | null;
  shipped_at: string;
}

export interface DeliveryConfirmation {
  id: string;
  shipment_id: string;
  received_by_user_id: string;
  notes: string | null;
  delivered_at: string;
}

export interface ReturnReceipt {
  id: string;
  shipment_id: string;
  reason_code: ReturnReasonCode;
  reason: string;
  inspection_notes: string | null;
  received_by_user_id: string;
  received_at: string;
}

export interface ReturnDecision {
  id: string;
  return_receipt_id: string;
  source_scan_file_version_id: string;
  reproduction_case_id: string | null;
  resolution: ReturnResolution;
  reason: string;
  decided_by_user_id: string;
  decided_at: string;
}

export interface CaseOperations {
  production_runs: ProductionRun[];
  production_completions: ProductionCompletion[];
  shipments: Shipment[];
  delivery_confirmations: DeliveryConfirmation[];
  return_receipts: ReturnReceipt[];
  return_decisions: ReturnDecision[];
}
