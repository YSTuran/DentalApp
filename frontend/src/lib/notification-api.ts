import type { NotificationListResponse } from "../types/notification";
import { apiRequest, csrfRequest } from "./api";

export function listNotifications(signal?: AbortSignal): Promise<NotificationListResponse> {
  return apiRequest<NotificationListResponse>("/api/notifications?limit=30", { signal });
}

export function dismissNotification(notificationId: string): Promise<void> {
  return csrfRequest<{ status: string }>(`/api/notifications/${notificationId}/dismiss`, {
    method: "POST",
  }).then(() => undefined);
}
