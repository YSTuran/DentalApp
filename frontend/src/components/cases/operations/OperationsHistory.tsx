import { formatDate } from "../../../lib/case-format";
import type { CaseOperations, ProductionRun } from "../../../types/fulfillment";

interface Props {
  operations: CaseOperations;
}

function eventRows(operations: CaseOperations, run: ProductionRun) {
  const completion = operations.production_completions.find(
    (item) => item.production_run_id === run.id,
  );
  const shipment = operations.shipments.find((item) => item.production_run_id === run.id);
  const delivery = shipment && operations.delivery_confirmations.find(
    (item) => item.shipment_id === shipment.id,
  );
  const receipt = shipment && operations.return_receipts.find(
    (item) => item.shipment_id === shipment.id,
  );
  const decision = receipt && operations.return_decisions.find(
    (item) => item.return_receipt_id === receipt.id,
  );
  return [
    { key: `start-${run.id}`, label: "Üretim başladı", detail: run.work_order_number, date: run.started_at },
    completion && { key: completion.id, label: "Üretim tamamlandı", detail: `${completion.material} · Lot ${completion.lot_number} · ${completion.quantity} adet`, date: completion.completed_at },
    shipment && { key: shipment.id, label: "Kargoya verildi", detail: `${shipment.carrier} · ${shipment.tracking_number}`, date: shipment.shipped_at },
    delivery && { key: delivery.id, label: "Şubeye teslim edildi", detail: delivery.notes ?? "Teslim doğrulandı", date: delivery.delivered_at },
    receipt && { key: receipt.id, label: "İade teslim alındı", detail: receipt.reason, date: receipt.received_at },
    decision && { key: decision.id, label: decision.resolution === "reproduction" ? "Yeniden üretim kararı" : "Yeni tarama kararı", detail: decision.reason, date: decision.decided_at },
  ].filter((item): item is { key: string; label: string; detail: string; date: string } => Boolean(item));
}

export function OperationsHistory({ operations }: Props) {
  if (operations.production_runs.length === 0) return null;
  return (
    <div className="operation-history">
      <h3>Üretim ve teslim geçmişi</h3>
      {[...operations.production_runs].reverse().map((run) => (
        <article key={run.id}>
          <div className="operation-attempt-heading"><strong>Üretim {run.attempt_number}</strong><span>{run.work_order_number}</span></div>
          <ol>
            {eventRows(operations, run).map((event) => (
              <li key={event.key}><i aria-hidden="true" /><div><strong>{event.label}</strong><span>{event.detail}</span><small>{formatDate(event.date)}</small></div></li>
            ))}
          </ol>
        </article>
      ))}
    </div>
  );
}
