import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { MeshStatusBadge } from "../components/cases/CaseStatusBadge";
import { hasMeshWarnings, meshReportItems } from "../lib/mesh-report";

it("uyarılı geçerli taramayı ayrı bir rozetle gösterir", () => {
  render(<MeshStatusBadge status="valid" hasWarnings />);

  expect(screen.getByText("İnceleme uyarısı")).toBeInTheDocument();
});

it("mesh raporundaki uyarıları güvenli biçimde okur", () => {
  const report = { warnings: ["mesh_open_boundary", 42, null] };

  expect(meshReportItems(report, "warnings")).toEqual(["mesh_open_boundary"]);
  expect(hasMeshWarnings(report)).toBe(true);
});
