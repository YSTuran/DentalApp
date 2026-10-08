import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthContext, type AuthContextValue } from "../auth/AuthContext";
import { CaseOperationsPanel } from "../components/cases/operations/CaseOperationsPanel";
import { WorkOrderCard } from "../components/cases/operations/WorkOrderCard";
import type { CurrentUser, RoleCode } from "../types/auth";
import type { DentalCase } from "../types/case";
import type { CaseOperations } from "../types/fulfillment";

const apiMocks = vi.hoisted(() => ({
  completeProduction: vi.fn(),
  confirmDelivery: vi.fn(),
  createShipment: vi.fn(),
  decideReturn: vi.fn(),
  getCaseOperations: vi.fn(),
  registerReturn: vi.fn(),
  startProduction: vi.fn(),
}));

vi.mock("../lib/fulfillment-api", () => apiMocks);
vi.mock("jsbarcode", () => ({ default: vi.fn() }));

const dentalCase: DentalCase = {
  id: "case-one",
  case_number: "VKA-2026-000001",
  clinic_id: "clinic-one",
  clinic_name: "Demo Klinik",
  responsible_dentist_name: "Demo Hekim",
  patient_code: "DEMO-001",
  status: "ready_for_production",
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
  file_versions: [{
    id: "design-one",
    kind: "design",
    version_number: 1,
    size_bytes: 100,
    mesh_status: "valid",
    mesh_report: null,
    is_locked: true,
    mesh_validation_attempts: 1,
    mesh_validated_at: "2026-10-05T08:00:00Z",
    created_at: "2026-10-05T08:00:00Z",
  }],
  approvals: [],
};

const operations: CaseOperations = {
  production_runs: [{
    id: "run-one",
    case_id: dentalCase.id,
    attempt_number: 1,
    design_file_version_id: "design-one",
    work_order_number: "ISE-2026-000001",
    started_by_user_id: "technician-one",
    notes: null,
    started_at: "2026-10-05T09:00:00Z",
  }],
  production_completions: [],
  shipments: [{
    id: "shipment-one",
    production_run_id: "run-one",
    destination_clinic_id: "clinic-one",
    carrier: "Demo Kargo",
    tracking_number: "TRACK-1",
    shipped_by_user_id: "technician-one",
    notes: null,
    shipped_at: "2026-10-05T10:00:00Z",
  }],
  delivery_confirmations: [],
  return_receipts: [{
    id: "return-one",
    shipment_id: "shipment-one",
    reason_code: "fit_issue",
    reason: "Ürün hastaya uymadı.",
    inspection_notes: null,
    received_by_user_id: "technician-one",
    received_at: "2026-10-05T11:00:00Z",
  }],
  return_decisions: [],
};

function authValue(role: RoleCode): AuthContextValue {
  const global = ["system_admin", "technician"].includes(role);
  const user: CurrentUser = {
    id: `${role}-one`,
    email: `${role}@example.invalid`,
    full_name: "Test User",
    global_roles: global ? [role] : [],
    clinic_roles: global ? [] : [{ clinic_id: "clinic-one", role }],
    preferences: { theme_mode: "light", color_palette: "default", updated_at: null },
  };
  return {
    status: "authenticated",
    user,
    login: vi.fn(),
    logout: vi.fn(),
    changePassword: vi.fn(),
    retrySession: vi.fn(),
  };
}

function renderPanel(
  role: RoleCode,
  currentCase: DentalCase,
  onUpdated = vi.fn(),
) {
  return render(
    <AuthContext.Provider value={authValue(role)}>
      <CaseOperationsPanel dentalCase={currentCase} onUpdated={onUpdated} />
    </AuthContext.Provider>,
  );
}

afterEach(() => {
  cleanup();
  document.body.classList.remove("printing-report");
});

beforeEach(() => {
  vi.clearAllMocks();
  apiMocks.getCaseOperations.mockResolvedValue(operations);
  apiMocks.startProduction.mockResolvedValue({ ...dentalCase, status: "in_production" });
  apiMocks.confirmDelivery.mockResolvedValue({ ...dentalCase, status: "delivered" });
  apiMocks.decideReturn.mockResolvedValue({
    ...dentalCase,
    id: "case-two",
    case_number: "VKA-2026-000002",
    status: "draft",
    reproduction_source_case_id: dentalCase.id,
    reproduction_source_case_number: dentalCase.case_number,
    file_versions: [],
    approvals: [],
  });
});

describe("üretim, teslim ve iade paneli", () => {
  it("barkodlu iş emrini tek düğmeyle yazdırır", async () => {
    const interaction = userEvent.setup();
    const printMock = vi.spyOn(window, "print").mockImplementation(() => undefined);
    render(
      <WorkOrderCard
        dentalCase={dentalCase}
        productionRun={operations.production_runs[0]}
        includeBarcode
      />,
    );

    expect(screen.getByText("Demo Hekim")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "VKA-2026-000001 barkodu" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Etiket yazdır" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "İş emrini yazdır" })).not.toBeInTheDocument();
    await interaction.click(screen.getByRole("button", { name: "Yazdır" }));
    await waitFor(() => expect(printMock).toHaveBeenCalledOnce());
    printMock.mockRestore();
  });

  it("teknisyen olmayan kullanıcıya barkodsuz iş emri yazdırır", async () => {
    const interaction = userEvent.setup();
    const printMock = vi.spyOn(window, "print").mockImplementation(() => undefined);
    renderPanel("clinic_staff", dentalCase);

    await screen.findByRole("heading", { name: "Üretim ve teslim geçmişi" });
    expect(screen.getByLabelText("Üretim iş emri")).toBeInTheDocument();
    expect(screen.queryByRole("img", { name: "VKA-2026-000001 barkodu" })).not.toBeInTheDocument();
    await interaction.click(screen.getByRole("button", { name: "Yazdır" }));
    await waitFor(() => expect(printMock).toHaveBeenCalledOnce());
    printMock.mockRestore();
  });

  it("teknisyen onaylı tasarımla üretimi başlatır", async () => {
    const interaction = userEvent.setup();
    renderPanel("technician", dentalCase);
    await interaction.click(await screen.findByRole("button", { name: "Üretimi başlat" }));
    expect(apiMocks.startProduction).toHaveBeenCalledWith("case-one", "design-one", null);
  });

  it("yalnızca şube rolü teslimi doğrulayabilir", async () => {
    const interaction = userEvent.setup();
    renderPanel("clinic_staff", { ...dentalCase, status: "shipped" });
    await interaction.click(await screen.findByRole("button", { name: "Teslim alındı" }));
    expect(apiMocks.confirmDelivery).toHaveBeenCalledWith("case-one", "shipment-one", null);
  });

  it("yönetici hekim iade kararında gerekçe girmeden ilerleyemez", async () => {
    const interaction = userEvent.setup();
    const onUpdated = vi.fn();
    renderPanel("managing_dentist", { ...dentalCase, status: "return_review" }, onUpdated);
    const button = await screen.findByRole("button", { name: "Kararı kaydet" });
    expect(button).toBeDisabled();
    await interaction.type(screen.getByLabelText("Karar gerekçesi *"), "Yeniden üretilmeli.");
    await interaction.click(button);
    expect(apiMocks.decideReturn).toHaveBeenCalledWith(
      "case-one",
      "return-one",
      "reproduction",
      "Yeniden üretilmeli.",
    );
    expect(onUpdated).toHaveBeenCalledWith(
      expect.objectContaining({ id: "case-two", status: "draft" }),
      "Bağlantılı yeniden üretim vakası taslak olarak oluşturuldu.",
    );
  });

  it("teslim edilen vakada normal işlemleri kapatıp yalnızca iade yolunu açar", async () => {
    const interaction = userEvent.setup();
    renderPanel("technician", { ...dentalCase, status: "delivered" });

    expect(await screen.findByText("Operasyon tamamlandı")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Üretimi başlat" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Kargoya ver" })).not.toBeInTheDocument();

    await interaction.click(screen.getByRole("button", { name: "İade kaydı oluştur" }));
    expect(screen.getByRole("heading", { name: "İadeyi teslim al" })).toBeInTheDocument();
  });
});
