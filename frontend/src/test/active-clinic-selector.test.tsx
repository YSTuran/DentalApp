import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AuthContext, type AuthContextValue } from "../auth/AuthContext";
import { ActiveClinicSelector } from "../components/ActiveClinicSelector";
import type { CurrentUser } from "../types/auth";

function authValue(user: CurrentUser, selectActiveClinic = vi.fn()): AuthContextValue {
  return {
    status: "authenticated",
    user,
    login: vi.fn(),
    logout: vi.fn(),
    changePassword: vi.fn(),
    retrySession: vi.fn(),
    selectActiveClinic,
  };
}

const manager: CurrentUser = {
  id: "manager",
  email: "manager@example.invalid",
  full_name: "Çoklu Klinik Yöneticisi",
  global_roles: [],
  clinic_roles: [
    { clinic_id: "clinic-a", clinic_name: "A Kliniği", role: "clinic_manager" },
    { clinic_id: "clinic-b", clinic_name: "B Kliniği", role: "clinic_manager" },
  ],
  preferences: {
    theme_mode: "light",
    color_palette: "default",
    active_clinic_id: null,
    updated_at: null,
  },
};

afterEach(cleanup);

describe("aktif klinik seçici", () => {
  it("yalnızca çoklu klinik yöneticisinde görünür ve tercihi kaydeder", async () => {
    const selectActiveClinic = vi.fn().mockResolvedValue(undefined);
    render(
      <AuthContext.Provider value={authValue(manager, selectActiveClinic)}>
        <ActiveClinicSelector />
      </AuthContext.Provider>,
    );

    await userEvent.selectOptions(screen.getByLabelText("Aktif klinik"), "clinic-b");
    expect(selectActiveClinic).toHaveBeenCalledWith("clinic-b");
  });

  it("tek klinik rolünde görünmez", () => {
    render(
      <AuthContext.Provider value={authValue({
        ...manager,
        clinic_roles: manager.clinic_roles.slice(0, 1),
      })}>
        <ActiveClinicSelector />
      </AuthContext.Provider>,
    );

    expect(screen.queryByLabelText("Aktif klinik")).not.toBeInTheDocument();
  });
});
