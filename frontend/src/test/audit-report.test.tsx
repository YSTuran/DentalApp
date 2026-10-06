import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { AuditReportDocument } from "../components/audit/AuditReportDocument";

it("audit raporunu aktif filtre ve kategori kutularıyla oluşturur", () => {
  const { container } = render(
    <AuditReportDocument
      events={[{
        id: "audit-one",
        action: "case.shipped",
        entity_type: "case",
        entity_id: "case-one",
        actor_user_id: "user-one",
        actor_email: "user@example.test",
        clinic_id: "clinic-one",
        reason: null,
        before_data: null,
        after_data: null,
        context: {},
        ip_address: "127.0.0.1",
        user_agent: null,
        created_at: "2026-10-06T08:00:00Z",
      }]}
      filters={{
        action: "case.shipped",
        entityType: "case",
        entityId: "",
        clinicId: "clinic-one",
        dateFrom: "2026-10-01",
        dateTo: "2026-10-06",
      }}
      clinicNames={new Map([["clinic-one", "Demo Klinik"]])}
    />,
  );

  expect(screen.getByText("Audit kayıtları raporu")).toBeInTheDocument();
  expect(screen.getByText("İşlem: Ürün kargoya verildi")).toBeInTheDocument();
  expect(screen.getByText("Klinik: Demo Klinik")).toBeInTheDocument();
  expect(container.querySelector(".audit-report-card.audit-tone-delivery")).not.toBeNull();
});
