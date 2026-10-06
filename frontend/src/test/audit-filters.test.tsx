import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { expect, it, vi } from "vitest";

import { AuditFilters } from "../components/audit/AuditFilters";
import { auditDateBoundaries } from "../lib/audit-date";
import { EMPTY_AUDIT_FILTERS, type AuditFilterValues } from "../lib/audit-filter-values";

it("audit filtrelerini seçimlerle otomatik günceller ve tek işlemle temizler", () => {
  const changed = vi.fn();
  function Harness() {
    const [filters, setFilters] = useState<AuditFilterValues>(EMPTY_AUDIT_FILTERS);
    return (
      <AuditFilters
        clinics={[]}
        value={filters}
        onChange={(next) => {
          changed(next);
          setFilters(next);
        }}
      />
    );
  }

  render(<Harness />);
  fireEvent.change(screen.getByLabelText("İşlem"), { target: { value: "case.shipped" } });
  fireEvent.change(screen.getByLabelText("Başlangıç tarihi"), { target: { value: "2026-10-05" } });

  expect(changed).toHaveBeenLastCalledWith(expect.objectContaining({
    action: "case.shipped",
    dateFrom: "2026-10-05",
  }));
  expect(screen.queryByRole("button", { name: "Filtrele" })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Temizle" }));
  expect(changed).toHaveBeenLastCalledWith(EMPTY_AUDIT_FILTERS);
});

it("bitiş tarihini kullanıcının yerel gününün sonrasındaki sınıra dönüştürür", () => {
  expect(auditDateBoundaries("2026-10-05", "2026-10-05")).toEqual({
    createdFrom: new Date(2026, 9, 5).toISOString(),
    createdBefore: new Date(2026, 9, 6).toISOString(),
  });
});
