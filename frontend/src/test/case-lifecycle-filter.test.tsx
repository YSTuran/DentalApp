import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { AuthContext, type AuthContextValue } from "../auth/AuthContext";
import { listCases } from "../lib/cases-api";
import { CasesPage } from "../pages/CasesPage";

vi.mock("../lib/cases-api", () => ({ listCases: vi.fn() }));
vi.mock("../components/DemoBanner", () => ({ DemoBanner: () => null }));
vi.mock("../components/OperationsHeader", () => ({ OperationsHeader: () => null }));

const listCasesMock = vi.mocked(listCases);
const authValue: AuthContextValue = {
  status: "authenticated",
  user: {
    id: "dentist-one",
    email: "dentist@example.invalid",
    full_name: "Demo Hekim",
    global_roles: [],
    clinic_roles: [{ clinic_id: "clinic-one", role: "dentist" }],
    preferences: { theme_mode: "light", color_palette: "default", updated_at: null },
  },
  login: vi.fn(),
  logout: vi.fn(),
  changePassword: vi.fn(),
  retrySession: vi.fn(),
};

beforeEach(() => {
  listCasesMock.mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

it("vaka listesini varsayılan olarak aktif işlere açar ve yaşam döngüsünü sunucuda filtreler", async () => {
  const interaction = userEvent.setup();
  render(
    <MemoryRouter>
      <AuthContext.Provider value={authValue}><CasesPage /></AuthContext.Provider>
    </MemoryRouter>,
  );

  await waitFor(() => expect(listCasesMock).toHaveBeenCalledWith(expect.objectContaining({
    lifecycle: "active",
    limit: 20,
    offset: 0,
  })));
  expect(screen.queryByRole("combobox")).not.toBeInTheDocument();

  await interaction.click(screen.getByRole("button", { name: "Tamamlanan" }));
  await waitFor(() => expect(listCasesMock).toHaveBeenLastCalledWith(expect.objectContaining({
    lifecycle: "completed",
  })));
});
