import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DentistDesignDecisionPanel } from "../components/cases/DentistDesignDecisionPanel";
import { LabDesignPanel } from "../components/cases/LabDesignPanel";
import type { DentalCase } from "../types/case";

const apiMocks = vi.hoisted(() => ({
  dentistDecideDesign: vi.fn(),
  submitDesign: vi.fn(),
}));

vi.mock("../lib/cases-api", () => apiMocks);
vi.mock("../hooks/useResumableUpload", () => ({
  useResumableUpload: () => ({
    phase: "idle",
    progress: 0,
    error: null,
    upload: vi.fn(),
    pause: vi.fn(),
  }),
}));

const dentalCase: DentalCase = {
  id: "case-one",
  case_number: "VKA-2026-000001",
  clinic_id: "clinic-one",
  clinic_name: "Demo Klinik",
  created_by_user_id: "dentist-one",
  responsible_dentist_user_id: "dentist-one",
  responsible_dentist_name: "Demo Hekim",
  patient_code: "DEMO-001",
  patient_name: "Demo Hasta",
  status: "dentist_review",
  submitted_at: "2026-10-02T08:00:00Z",
  cancelled_at: null,
  created_at: "2026-10-02T07:00:00Z",
  updated_at: "2026-10-02T08:00:00Z",
  details: {
    appliance_type: "Şeffaf plak",
    material: "PET-G",
    tooth_numbers: ["11"],
    special_notes: null,
    extra_fields: {},
  },
  file_versions: [
    {
      id: "design-v1",
      kind: "design",
      version_number: 1,
      size_bytes: 100,
      mesh_status: "valid",
      mesh_report: null,
      is_locked: false,
      mesh_validation_attempts: 1,
      mesh_validated_at: "2026-10-02T08:10:00Z",
      created_at: "2026-10-02T08:00:00Z",
    },
    {
      id: "design-v2",
      kind: "design",
      version_number: 2,
      size_bytes: 120,
      mesh_status: "valid",
      mesh_report: null,
      is_locked: false,
      mesh_validation_attempts: 1,
      mesh_validated_at: "2026-10-02T08:30:00Z",
      created_at: "2026-10-02T08:20:00Z",
    },
  ],
  approvals: [],
};

afterEach(cleanup);

beforeEach(() => {
  vi.clearAllMocks();
  apiMocks.submitDesign.mockResolvedValue({ ...dentalCase, status: "dentist_review" });
  apiMocks.dentistDecideDesign.mockResolvedValue({
    ...dentalCase,
    status: "ready_for_production",
  });
});

describe("laboratuvar tasarım ve hekim onay panelleri", () => {
  it("laboratuvar yalnızca son geçerli tasarım sürümünü hekime gönderir", async () => {
    const interaction = userEvent.setup();
    render(
      <LabDesignPanel
        dentalCase={{ ...dentalCase, status: "lab_design" }}
        userId="technician-one"
        onRefresh={vi.fn()}
        onUpdated={vi.fn()}
      />,
    );

    await interaction.click(screen.getByRole("button", { name: "Hekim onayına gönder" }));
    expect(apiMocks.submitDesign).toHaveBeenCalledWith("case-one", "design-v2");
  });

  it("hekim onaydan önce geri alınamazlık kutusunu zorunlu tutar", async () => {
    const interaction = userEvent.setup();
    render(<DentistDesignDecisionPanel dentalCase={dentalCase} onUpdated={vi.fn()} />);

    await interaction.click(screen.getByRole("button", { name: "Tasarımı onayla" }));
    const dialog = screen.getByRole("dialog");
    const confirmButton = within(dialog).getByRole("button", { name: "Onayı kesinleştir" });
    expect(confirmButton).toBeDisabled();

    await interaction.click(within(dialog).getByRole("checkbox"));
    await interaction.click(confirmButton);
    expect(apiMocks.dentistDecideDesign).toHaveBeenCalledWith(
      "case-one",
      "approved",
      "design-v2",
      null,
    );
  });

  it("tasarım düzeltme talebinde gerekçeyi zorunlu tutar", async () => {
    const interaction = userEvent.setup();
    render(<DentistDesignDecisionPanel dentalCase={dentalCase} onUpdated={vi.fn()} />);

    await interaction.click(screen.getByRole("button", { name: "Düzeltme iste" }));
    const dialog = screen.getByRole("dialog");
    const submitButton = within(dialog).getByRole("button", { name: "Düzeltme iste" });
    expect(submitButton).toBeDisabled();
    await interaction.type(within(dialog).getByLabelText("Düzeltme gerekçesi *"), "Kenarları düzeltin.");
    expect(submitButton).toBeEnabled();
  });
});
