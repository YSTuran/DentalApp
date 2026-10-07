import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CaseTransferPanel } from "../components/cases/CaseTransferPanel";
import type { CurrentUser } from "../types/auth";
import type { CaseTransfer, DentalCase } from "../types/case";

const apiMocks = vi.hoisted(() => ({
  decideCaseTransfer: vi.fn(),
  getCaseTransferOptions: vi.fn(),
  getCaseTransfers: vi.fn(),
  requestCaseTransfer: vi.fn(),
}));

vi.mock("../lib/cases-api", () => apiMocks);

const dentalCase: DentalCase = {
  id: "case-one",
  case_number: "VKA-2026-000001",
  clinic_id: "clinic-one",
  clinic_name: "Demo Klinik",
  responsible_dentist_user_id: "dentist-one",
  responsible_dentist_name: "Mevcut Hekim",
  patient_code: "DEMO-001",
  status: "manager_review",
  submitted_at: "2026-10-05T08:00:00Z",
  cancelled_at: null,
  created_at: "2026-10-05T07:00:00Z",
  updated_at: "2026-10-05T08:00:00Z",
  details: {
    appliance_type: "Şeffaf plak",
    material: "PET-G",
    tooth_numbers: ["11"],
    special_notes: null,
    extra_fields: {},
  },
  file_versions: [],
  approvals: [],
};

function currentUser(id: string, role: "clinic_manager" | "dentist"): CurrentUser {
  return {
    id,
    email: `${id}@example.test`,
    full_name: "Test Kullanıcı",
    global_roles: [],
    clinic_roles: [{ clinic_id: dentalCase.clinic_id, role }],
    preferences: { theme_mode: "light", color_palette: "default", updated_at: null },
  };
}

const pendingTransfer: CaseTransfer = {
  id: "transfer-one",
  case_id: dentalCase.id,
  from_dentist_user_id: "dentist-one",
  from_dentist_name: "Mevcut Hekim",
  to_dentist_user_id: "dentist-two",
  to_dentist_name: "Yeni Hekim",
  requested_by_user_id: "manager-one",
  requested_by_name: "Klinik Yöneticisi",
  decided_by_user_id: null,
  decided_by_name: null,
  status: "pending",
  request_reason: "Hekim izinli olduğu için devir istendi.",
  decision_reason: null,
  requested_at: "2026-10-06T08:00:00Z",
  decided_at: null,
};

afterEach(cleanup);

beforeEach(() => {
  vi.clearAllMocks();
  apiMocks.getCaseTransfers.mockResolvedValue({ items: [] });
  apiMocks.getCaseTransferOptions.mockResolvedValue({
    items: [{ id: "dentist-two", full_name: "Yeni Hekim" }],
  });
  apiMocks.requestCaseTransfer.mockResolvedValue(pendingTransfer);
  apiMocks.decideCaseTransfer.mockResolvedValue({
    ...pendingTransfer,
    status: "accepted",
    decided_by_user_id: "dentist-two",
    decided_by_name: "Yeni Hekim",
    decided_at: "2026-10-06T09:00:00Z",
  });
});

describe("vaka devri paneli", () => {
  it("klinik yöneticisinin hedef hekim ve gerekçe ile talep oluşturmasını sağlar", async () => {
    const interaction = userEvent.setup();
    render(
      <CaseTransferPanel
        dentalCase={dentalCase}
        user={currentUser("manager-one", "clinic_manager")}
        onChanged={vi.fn()}
      />,
    );

    await screen.findByRole("option", { name: "Yeni Hekim" });
    await interaction.type(
      screen.getByLabelText("Devir gerekçesi"),
      "Hekim izinli olduğu için",
    );
    await interaction.click(screen.getByRole("button", { name: "Devir talebi gönder" }));

    await waitFor(() => expect(apiMocks.requestCaseTransfer).toHaveBeenCalledWith(
      dentalCase.id,
      "dentist-two",
      "Hekim izinli olduğu için",
    ));
  });

  it("hedef hekimin bekleyen devri açık onayla kabul etmesini sağlar", async () => {
    apiMocks.getCaseTransfers.mockResolvedValue({ items: [pendingTransfer] });
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    const onChanged = vi.fn();
    const interaction = userEvent.setup();
    render(
      <CaseTransferPanel
        dentalCase={dentalCase}
        user={currentUser("dentist-two", "dentist")}
        onChanged={onChanged}
      />,
    );

    await interaction.click(await screen.findByRole("button", { name: "Kabul et" }));

    await waitFor(() => expect(apiMocks.decideCaseTransfer).toHaveBeenCalledWith(
      dentalCase.id,
      pendingTransfer.id,
      "accepted",
      null,
    ));
    expect(onChanged).toHaveBeenCalledOnce();
    confirm.mockRestore();
  });
});
