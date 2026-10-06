import { useCallback, useEffect, useMemo, useState } from "react";

import { useAuth } from "../../../auth/AuthContext";
import { getCaseOperations } from "../../../lib/fulfillment-api";
import type { DentalCase } from "../../../types/case";
import type { CaseOperations } from "../../../types/fulfillment";
import {
  DeliveryConfirmAction,
  ReturnDecisionAction,
  ReturnReceiptAction,
} from "./DeliveryReturnActions";
import { OperationsHistory } from "./OperationsHistory";
import {
  ProductionCompleteAction,
  ProductionStartAction,
  ShipmentCreateAction,
} from "./ProductionActions";
import { WorkOrderCard } from "./WorkOrderCard";

interface Props {
  dentalCase: DentalCase;
  onUpdated: (updated: DentalCase, message: string) => void;
}

const startStatuses = new Set(["ready_for_production", "reproduction_requested"]);

export function CaseOperationsPanel({ dentalCase, onUpdated }: Props) {
  const { user } = useAuth();
  const [operations, setOperations] = useState<CaseOperations | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setOperations(await getCaseOperations(dentalCase.id));
      setError(null);
    } catch {
      setError("Üretim ve teslim kayıtları yüklenemedi.");
    } finally {
      setLoading(false);
    }
  }, [dentalCase.id]);

  useEffect(() => {
    // The request synchronizes the operation panel with the selected case.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load, dentalCase.status]);

  const latestRun = useMemo(() => operations?.production_runs.at(-1), [operations]);
  const latestShipment = useMemo(
    () => [...(operations?.shipments ?? [])]
      .reverse()
      .find((item) => item.production_run_id === latestRun?.id),
    [latestRun, operations],
  );
  const latestReceipt = useMemo(
    () => [...(operations?.return_receipts ?? [])]
      .reverse()
      .find((item) => item.shipment_id === latestShipment?.id),
    [latestShipment, operations],
  );
  const isTechnician = user?.global_roles.includes("technician") === true;
  const hasClinicRole = (roles: string[]) => user?.clinic_roles.some((assignment) => (
    assignment.clinic_id === dentalCase.clinic_id && roles.includes(assignment.role)
  )) === true;

  function handleUpdated(updated: DentalCase, message: string) {
    onUpdated(updated, message);
    void load();
  }

  if (loading) return <section className="case-panel operation-panel">Operasyon kayıtları yükleniyor…</section>;
  return (
    <section className="case-panel operation-panel">
      <div className="panel-heading"><div><p className="card-label">ÜRETİM VE TESLİM</p><h2>Operasyon takibi</h2></div></div>
      <p className="panel-description">Üretim, kargo, şube teslimi ve iade kayıtları eski kayıtların üzerine yazılmadan saklanır.</p>
      {error && <div className="form-error" role="alert">{error}</div>}
      {operations && latestRun && <WorkOrderCard dentalCase={dentalCase} productionRun={latestRun} />}

      {dentalCase.status === "delivered" && (
        <div className="operation-complete-state">
          <strong>Operasyon tamamlandı</strong>
          <span>Üretim ve teslim işlemleri kapalıdır. Ürün geri geldiyse yalnızca iade kaydı oluşturulabilir.</span>
        </div>
      )}

      {isTechnician && startStatuses.has(dentalCase.status) && <ProductionStartAction dentalCase={dentalCase} onUpdated={handleUpdated} />}
      {isTechnician && dentalCase.status === "in_production" && latestRun && <ProductionCompleteAction dentalCase={dentalCase} productionRun={latestRun} onUpdated={handleUpdated} />}
      {isTechnician && dentalCase.status === "production_completed" && latestRun && <ShipmentCreateAction dentalCase={dentalCase} productionRun={latestRun} onUpdated={handleUpdated} />}
      {dentalCase.status === "shipped" && latestShipment && hasClinicRole(["clinic_manager", "clinic_staff"]) && <DeliveryConfirmAction dentalCase={dentalCase} shipment={latestShipment} onUpdated={handleUpdated} />}
      {isTechnician && dentalCase.status === "delivered" && latestShipment && <ReturnReceiptAction dentalCase={dentalCase} shipment={latestShipment} onUpdated={handleUpdated} />}
      {dentalCase.status === "return_review" && latestReceipt && hasClinicRole(["managing_dentist"]) && <ReturnDecisionAction dentalCase={dentalCase} receipt={latestReceipt} onUpdated={handleUpdated} />}

      {operations && <OperationsHistory operations={operations} />}
    </section>
  );
}
