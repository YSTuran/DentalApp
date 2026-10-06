import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { AuthContext, type AuthContextValue } from "../auth/AuthContext";
import { listCases } from "../lib/cases-api";
import { DashboardPage } from "../pages/DashboardPage";
import type { CurrentUser, RoleCode } from "../types/auth";

vi.mock("../lib/cases-api", () => ({ listCases: vi.fn() }));

const listCasesMock = vi.mocked(listCases);

function currentUser(role: RoleCode): CurrentUser {
  const isGlobalRole = role === "system_admin" || role === "technician";
  return {
    id: "9b2b1354-2454-4196-859c-daa00f27cf3e",
    email: "user@example.test",
    full_name: "Test Kullanıcısı",
    global_roles: isGlobalRole ? [role] : [],
    clinic_roles: isGlobalRole ? [] : [{ clinic_id: "clinic-1", role }],
    preferences: { theme_mode: "light", color_palette: "default", updated_at: null },
  };
}

function renderDashboard(role: RoleCode) {
  const value: AuthContextValue = {
    status: "authenticated",
    user: currentUser(role),
    login: vi.fn(),
    logout: vi.fn(),
    changePassword: vi.fn(),
    retrySession: vi.fn(),
  };
  render(
    <MemoryRouter>
      <AuthContext.Provider value={value}><DashboardPage /></AuthContext.Provider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  listCasesMock.mockImplementation(async ({ status } = {}) => ({
    items: [],
    total: status === "manager_review" ? 3 : 1,
    limit: 1,
    offset: 0,
  }));
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

it("yönetici hekime yönetim kartı yerine onay kuyruğunu gösterir", async () => {
  renderDashboard("managing_dentist");

  expect(screen.queryByText("Klinik personeli görünümü")).not.toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Onay bekleyen vakalar" })).toBeInTheDocument();
  expect(await screen.findByText("3")).toBeInTheDocument();
  expect(screen.getByText("1")).toBeInTheDocument();
});

it("klinik yöneticisine yalnızca klinik yönetimi kartını gösterir", () => {
  renderDashboard("clinic_manager");

  expect(screen.getByRole("heading", { name: "Klinik personeli görünümü" })).toBeInTheDocument();
  expect(screen.queryByText("Onay bekleyen vakalar")).not.toBeInTheDocument();
  expect(listCasesMock).not.toHaveBeenCalled();
});

it("rol bilgisini kullanıcı kartında gösterir ve ayrı yetkiler kartını kaldırır", () => {
  renderDashboard("technician");

  expect(screen.getByText("Yetki")).toBeInTheDocument();
  expect(screen.getByText("Laboratuvar teknisyeni")).toBeInTheDocument();
  expect(screen.queryByText("YETKİLER")).not.toBeInTheDocument();
  expect(screen.queryByText(/klinik rolü atanmış/i)).not.toBeInTheDocument();
});
