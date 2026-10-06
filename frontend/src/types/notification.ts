export interface UserNotification {
  id: string;
  kind: string;
  title: string;
  message: string;
  target_path: string | null;
  created_at: string;
}

export interface NotificationListResponse {
  items: UserNotification[];
  total: number;
}
