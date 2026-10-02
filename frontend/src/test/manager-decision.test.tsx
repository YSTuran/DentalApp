import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ManagerDecisionPanel } from "../components/cases/ManagerDecisionPanel";
import type { CurrentUser } from "../types/auth";
import type { DentalCase } from "../types/case";

const apiMocks = vi.hoisted(() => ({
  managerDecideCase: vi.fn(),
}));

vi.mock("../lib/cases-api", () => apiMocks);

const user: CurrentUser = {
  id: "manager-user",
  email: "manager@example.test",
  full_name: "Demo Yönetici",
  global_roles: [],
  clinic_roles: [{ clinic_id: "clinic-one", role: "managing_dentist" }],
  preferences: {
    theme_mode: "light",
    color_palette: "default",
    updated_at: null,
  },
};

const dentalCase: DentalCase = {
  id: "case-one",
  case_number: "VKA-2026-000001",
  clinic_id: "clinic-one",
  clinic_name: "Demo Klinik",
  created_by_user_id: "dentist-user",
  responsible_dentist_user_id: "dentist-user",
  responsible_dentist_name: "Demo Hekim",
  patient_code: "DEMO-001",
  patient_name: "Demo Hasta",
  status: "manager_review",
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
      id: "scan-v1",
      kind: "scan",
      version_number: 1,
      original_filename: "scan-v1.stl",
      size_bytes: 100,
      mesh_status: "valid",
      mesh_report: null,
      is_locked: false,
      mesh_validation_attempts: 1,
      mesh_validated_at: "2026-10-02T07:30:00Z",
      uploaded_by_user_id: "dentist-user",
      created_at: "2026-10-02T07:20:00Z",
    },
    {
      id: "scan-v2",
      kind: "scan",
      version_number: 2,
      original_filename: "scan-v2.stl",
      size_bytes: 120,
      mesh_status: "valid",
      mesh_report: null,
      is_locked: false,
      mesh_validation_attempts: 1,
      mesh_validated_at: "2026-10-02T07:50:00Z",
      uploaded_by_user_id: "dentist-user",
      created_at: "2026-10-02T07:40:00Z",
    },
  ],
  approvals: [],
};

afterEach(cleanup);

beforeEach(() => {
  vi.clearAllMocks();
  apiMocks.managerDecideCase.mockResolvedValue({
    ...dentalCase,
    status: "lab_design",
  });
});

describe("yönetici hekim kararı", () => {
  it("geri alınamaz onayı son tarama sürümüne bağlar", async () => {
    const onUpdated = vi.fn();
    const interaction = userEvent.setup();
    render(<ManagerDecisionPanel dentalCase={dentalCase} user={user} onUpdated={onUpdated} />);

    await interaction.click(screen.getByRole("button", { name: "Onayla" }));
    const confirmButton = screen.getByRole("button", { name: "Onayı kesinleştir" });
    expect(confirmButton).toBeDisabled();

    await interaction.click(screen.getByRole("checkbox"));
    await interaction.click(confirmButton);

    expect(apiMocks.managerDecideCase).toHaveBeenCalledWith(
      "case-one",
      "approved",
      "scan-v2",
      null,
    );
    expect(onUpdated).toHaveBeenCalledOnce();
  });

  it("düzeltme talebinde gerekçeyi zorunlu tutar", async () => {
    const interaction = userEvent.setup();
    render(<ManagerDecisionPanel dentalCase={dentalCase} user={user} onUpdated={vi.fn()} />);

    await interaction.click(screen.getByRole("button", { name: "Düzeltme iste" }));
    const dialog = screen.getByRole("dialog");
    const submitButton = within(dialog).getByRole("button", { name: "Düzeltme iste" });
    expect(submitButton).toBeDisabled();
    await interaction.type(screen.getByLabelText("Karar gerekçesi *"), "Tarama eksik.");
    expect(submitButton).toBeEnabled();
  });

  it("yönetici kendi vakasını inceliyorsa görünür uyarı verir", () => {
    render(
      <ManagerDecisionPanel
        dentalCase={{ ...dentalCase, created_by_user_id: user.id }}
        user={user}
        onUpdated={vi.fn()}
      />,
    );

    expect(screen.getByText(/yönetici kendi vakasını onayladı/i)).toBeInTheDocument();
  });
});
