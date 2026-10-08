import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";

import { AuthContext, type AuthContextValue } from "../auth/AuthContext";
import { OperationsHeader } from "../components/OperationsHeader";
import type { CurrentUser, RoleCode } from "../types/auth";

vi.mock("../components/ActiveClinicSelector", () => ({ ActiveClinicSelector: () => null }));
vi.mock("../components/NotificationBell", () => ({ NotificationBell: () => null }));

function renderHeader(role: RoleCode) {
  const user: CurrentUser = {
    id: "user-one",
    email: "user@example.test",
    full_name: "Demo Kullanıcı",
    global_roles: role === "system_admin" || role === "technician" ? [role] : [],
    clinic_roles: role === "system_admin" || role === "technician"
      ? []
      : [{ clinic_id: "clinic-one", role }],
    preferences: { theme_mode: "light", color_palette: "default", updated_at: null },
  };
  const value: AuthContextValue = {
    status: "authenticated",
    user,
    login: vi.fn(),
    logout: vi.fn(),
    changePassword: vi.fn(),
    retrySession: vi.fn(),
    selectActiveClinic: vi.fn(),
  };
  return render(
    <MemoryRouter>
      <AuthContext.Provider value={value}>
        <OperationsHeader />
      </AuthContext.Provider>
    </MemoryRouter>,
  );
}

afterEach(cleanup);

it("rapor bağlantısını hekimden gizleyip yönetici hekimde gösterir", () => {
  const { unmount } = renderHeader("dentist");
  expect(screen.queryByRole("link", { name: "Raporlar" })).not.toBeInTheDocument();
  unmount();

  renderHeader("managing_dentist");
  expect(screen.getByRole("link", { name: "Raporlar" })).toBeInTheDocument();
});
