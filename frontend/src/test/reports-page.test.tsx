import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthContext, type AuthContextValue } from "../auth/AuthContext";
import { ReportsPage } from "../pages/ReportsPage";
import type { CurrentUser } from "../types/auth";
import type { CaseReport } from "../types/report";

const getCaseReport = vi.hoisted(() => vi.fn());

vi.mock("../lib/reports-api", () => ({ getCaseReport }));
vi.mock("../components/OperationsHeader", () => ({
  OperationsHeader: () => <header>DentalApp</header>,
}));

const report: CaseReport = {
  date_from: null,
  date_to: null,
  clinic_id: "clinic-one",
  generated_at: "2026-10-07T08:00:00Z",
  totals: {
    total: 12,
    active: 5,
    completed: 6,
    closed: 7,
    returned: 2,
    reproductions: 1,
    overdue: 1,
    average_completion_hours: 28.5,
  },
  status_counts: [{ key: "draft", label: "Taslak", count: 3 }],
  clinic_counts: [{ id: "clinic-one", name: "Birinci Klinik", count: 12 }],
  dentist_counts: [{ id: "dentist-one", full_name: "Demo Hekim", count: 8 }],
  stage_durations: [{ status: "manager_review", average_hours: 4, sample_size: 6 }],
  available_clinics: [
    { id: "clinic-one", name: "Birinci Klinik", count: 12 },
    { id: "clinic-two", name: "İkinci Klinik", count: 4 },
  ],
};

const user: CurrentUser = {
  id: "manager-one",
  email: "manager@example.test",
  full_name: "Klinik Yöneticisi",
  global_roles: [],
  clinic_roles: [
    { clinic_id: "clinic-one", clinic_name: "Birinci Klinik", role: "clinic_manager" },
    { clinic_id: "clinic-two", clinic_name: "İkinci Klinik", role: "clinic_manager" },
  ],
  preferences: {
    theme_mode: "light",
    color_palette: "default",
    active_clinic_id: "clinic-one",
    updated_at: null,
  },
};

const authValue: AuthContextValue = {
  status: "authenticated",
  user,
  login: vi.fn(),
  logout: vi.fn(),
  changePassword: vi.fn(),
  retrySession: vi.fn(),
  selectActiveClinic: vi.fn(),
};

afterEach(cleanup);

beforeEach(() => {
  vi.clearAllMocks();
  getCaseReport.mockResolvedValue(report);
});

describe("vaka raporları", () => {
  it("aktif klinik kapsamını kullanır ve operasyon metriklerini gösterir", async () => {
    render(
      <MemoryRouter>
        <AuthContext.Provider value={authValue}>
          <ReportsPage />
        </AuthContext.Provider>
      </MemoryRouter>,
    );

    expect(await screen.findByText("12")).toBeInTheDocument();
    expect(screen.getByText("Demo Hekim")).toBeInTheDocument();
    expect(screen.getByText("28,5 sa")).toBeInTheDocument();
    expect(getCaseReport).toHaveBeenCalledWith(
      { clinicId: "clinic-one", dateFrom: undefined, dateTo: undefined },
      expect.any(AbortSignal),
    );
  });

  it("filtre değişikliklerini beklemeden yeni rapor sorgusuna uygular", async () => {
    const interaction = userEvent.setup();
    render(
      <MemoryRouter>
        <AuthContext.Provider value={authValue}>
          <ReportsPage />
        </AuthContext.Provider>
      </MemoryRouter>,
    );

    await screen.findByText("Demo Hekim");
    await interaction.selectOptions(screen.getByLabelText("Klinik"), "clinic-two");
    await interaction.type(screen.getByLabelText("Başlangıç"), "2026-10-01");

    await waitFor(() => expect(getCaseReport).toHaveBeenLastCalledWith(
      { clinicId: "clinic-two", dateFrom: "2026-10-01", dateTo: undefined },
      expect.any(AbortSignal),
    ));
  });
});
