import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { NotificationBell } from "../components/NotificationBell";
import { dismissNotification, listNotifications } from "../lib/notification-api";

vi.mock("../lib/notification-api", () => ({
  dismissNotification: vi.fn(),
  listNotifications: vi.fn(),
}));

const listMock = vi.mocked(listNotifications);
const dismissMock = vi.mocked(dismissNotification);

beforeEach(() => {
  listMock.mockResolvedValue({
    total: 1,
    items: [{
      id: "notification-one",
      kind: "case.design_submitted",
      title: "Tasarım onayı bekleniyor",
      message: "VKA-2026-000001 tasarım onayınıza gönderildi.",
      target_path: "/vakalar/case-one",
      created_at: "2026-10-06T08:00:00Z",
    }],
  });
  dismissMock.mockResolvedValue(undefined);
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

it("bildirime tıklayınca kapatır ve güvenli hedefe yönlendirir", async () => {
  const interaction = userEvent.setup();
  render(
    <MemoryRouter initialEntries={["/"]}>
      <NotificationBell />
      <Routes><Route path="/vakalar/:caseId" element={<div>Vaka hedefi</div>} /></Routes>
    </MemoryRouter>,
  );

  await waitFor(() => expect(listMock).toHaveBeenCalled());
  await interaction.click(screen.getByRole("button", { name: /Bildirimler, 1 okunmamış/i }));
  await interaction.click(screen.getByRole("button", { name: /Tasarım onayı bekleniyor/i }));

  expect(dismissMock).toHaveBeenCalledWith("notification-one");
  expect(await screen.findByText("Vaka hedefi")).toBeInTheDocument();
});

it("okundu düğmesi bildirimi yönlendirmeden kaldırır", async () => {
  const interaction = userEvent.setup();
  render(<MemoryRouter><NotificationBell /></MemoryRouter>);

  await waitFor(() => expect(listMock).toHaveBeenCalled());
  await interaction.click(screen.getByRole("button", { name: /Bildirimler, 1 okunmamış/i }));
  await interaction.click(screen.getByRole("button", { name: "Okundu" }));

  await waitFor(() => expect(screen.queryByText("Tasarım onayı bekleniyor")).not.toBeInTheDocument());
  expect(dismissMock).toHaveBeenCalledWith("notification-one");
});
