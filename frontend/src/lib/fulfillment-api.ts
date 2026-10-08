import { apiRequest, csrfRequest } from "./api";
import type { DentalCase } from "../types/case";
import type { CaseOperations, ReturnReasonCode, ReturnResolution } from "../types/fulfillment";

export function getCaseOperations(
  caseId: string,
  signal?: AbortSignal,
): Promise<CaseOperations> {
  return apiRequest(`/api/cases/${caseId}/operations`, { signal });
}

export function startProduction(
  caseId: string,
  designFileVersionId: string,
  notes: string | null,
): Promise<DentalCase> {
  return csrfRequest(`/api/cases/${caseId}/production/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ design_file_version_id: designFileVersionId, notes }),
  });
}

export function completeProduction(
  caseId: string,
  productionRunId: string,
  payload: { material: string; lot_number: string; quantity: number; notes: string | null },
): Promise<DentalCase> {
  return csrfRequest(`/api/cases/${caseId}/production/complete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ production_run_id: productionRunId, ...payload }),
  });
}

export function createShipment(
  caseId: string,
  productionRunId: string,
  payload: { carrier: string; tracking_number: string; notes: string | null },
): Promise<DentalCase> {
  return csrfRequest(`/api/cases/${caseId}/shipments`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ production_run_id: productionRunId, ...payload }),
  });
}

export function confirmDelivery(
  caseId: string,
  shipmentId: string,
  notes: string | null,
): Promise<DentalCase> {
  return csrfRequest(`/api/cases/${caseId}/delivery-confirmation`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ shipment_id: shipmentId, notes }),
  });
}

export function registerReturn(
  caseId: string,
  shipmentId: string,
  payload: { reason_code: ReturnReasonCode; reason: string; inspection_notes: string | null },
): Promise<DentalCase> {
  return csrfRequest(`/api/cases/${caseId}/returns`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ shipment_id: shipmentId, ...payload }),
  });
}

export function decideReturn(
  caseId: string,
  returnReceiptId: string,
  resolution: ReturnResolution,
  reason: string,
): Promise<DentalCase> {
  return csrfRequest(`/api/cases/${caseId}/return-decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ return_receipt_id: returnReceiptId, resolution, reason }),
  });
}
