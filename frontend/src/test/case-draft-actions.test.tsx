import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CaseCancelDialog } from "../components/cases/CaseCancelDialog";
import { CaseEditDialog } from "../components/cases/CaseEditDialog";
import type { DentalCase } from "../types/case";

const apiMocks = vi.hoisted(() => ({
  cancelCase: vi.fn(),
  getCaseCreateOptions: vi.fn(),
  updateCase: vi.fn(),
}));

vi.mock("../lib/cases-api", () => apiMocks);

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
  status: "draft",
  submitted_at: null,
  cancelled_at: null,
  created_at: "2026-10-02T07:00:00Z",
  updated_at: "2026-10-02T07:00:00Z",
  details: {
    appliance_type: "Şeffaf plak",
    material: "PET-G",
    tooth_numbers: ["11", "12"],
    special_notes: "Demo not",
    extra_fields: { renk: "şeffaf" },
  },
  file_versions: [],
  approvals: [],
};

afterEach(cleanup);

beforeEach(() => {
  vi.clearAllMocks();
  apiMocks.getCaseCreateOptions.mockResolvedValue({
    clinics: [{
      id: "clinic-one",
      code: "K001",
      name: "Demo Klinik",
      dentists: [{ id: "dentist-one", full_name: "Demo Hekim" }],
    }],
  });
  apiMocks.updateCase.mockResolvedValue({ ...dentalCase, patient_code: "DEMO-002" });
  apiMocks.cancelCase.mockResolvedValue({ ...dentalCase, status: "cancelled" });
});

describe("taslak vaka işlemleri", () => {
  it("değiştirilen form alanlarını mevcut vaka üzerinde günceller", async () => {
    const interaction = userEvent.setup();
    render(<CaseEditDialog dentalCase={dentalCase} onUpdated={vi.fn()} />);
    await interaction.click(screen.getByRole("button", { name: "Taslağı düzenle" }));

    const dialog = screen.getByRole("dialog");
    const codeInput = within(dialog).getByLabelText("Hasta kodu *");
    await interaction.clear(codeInput);
    await interaction.type(codeInput, "DEMO-002");
    await interaction.click(within(dialog).getByRole("button", { name: "Değişiklikleri kaydet" }));

    await waitFor(() => expect(apiMocks.updateCase).toHaveBeenCalledWith(
      "case-one",
      expect.objectContaining({
        responsible_dentist_user_id: "dentist-one",
        patient_code: "DEMO-002",
        tooth_numbers: ["11", "12"],
        extra_fields: { renk: "şeffaf" },
      }),
    ));
  });

  it("iptal için gerekçe ve açık onay ister", async () => {
    const interaction = userEvent.setup();
    render(<CaseCancelDialog dentalCase={dentalCase} onUpdated={vi.fn()} />);
    await interaction.click(screen.getByRole("button", { name: "Vakayı iptal et" }));

    const dialog = screen.getByRole("alertdialog");
    const cancelButton = within(dialog).getByRole("button", { name: "Vakayı iptal et" });
    expect(cancelButton).toBeDisabled();
    await interaction.type(within(dialog).getByLabelText("İptal gerekçesi *"), "Yanlış kayıt");
    await interaction.click(within(dialog).getByRole("checkbox"));
    await interaction.click(cancelButton);

    expect(apiMocks.cancelCase).toHaveBeenCalledWith("case-one", "Yanlış kayıt");
  });
});
