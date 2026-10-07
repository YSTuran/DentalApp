import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { dismissNotification, listNotifications } from "../lib/notification-api";
import type { UserNotification } from "../types/notification";
import "../notification.css";

function formatNotificationDate(value: string): string {
  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function safeTargetPath(value: string | null): string | null {
  return value?.startsWith("/") && !value.startsWith("//") ? value : null;
}

export function NotificationBell() {
  const navigate = useNavigate();
  const containerRef = useRef<HTMLDivElement>(null);
  const [items, setItems] = useState<UserNotification[]>([]);
  const [total, setTotal] = useState(0);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    try {
      const result = await listNotifications(signal);
      setItems(result.items);
      setTotal(result.total);
      setError(null);
    } catch {
      if (!signal?.aborted) setError("Bildirimler alınamadı.");
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const initialTimer = window.setTimeout(() => void load(controller.signal), 0);
    const timer = window.setInterval(() => void load(controller.signal), 30_000);
    return () => {
      controller.abort();
      window.clearTimeout(initialTimer);
      window.clearInterval(timer);
    };
  }, [load]);

  useEffect(() => {
    if (!open) return;
    const close = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const closeWithEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", closeWithEscape);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", closeWithEscape);
    };
  }, [open]);

  async function dismiss(item: UserNotification, followTarget: boolean) {
    setBusyId(item.id);
    setError(null);
    try {
      await dismissNotification(item.id);
      setItems((current) => current.filter((entry) => entry.id !== item.id));
      setTotal((current) => Math.max(0, current - 1));
      const target = followTarget ? safeTargetPath(item.target_path) : null;
      if (target) {
        setOpen(false);
        navigate(target);
      }
    } catch {
      setError("Bildirim kapatılamadı.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="notification-center" ref={containerRef}>
      <button
        className="notification-bell"
        type="button"
        aria-label={total > 0 ? `Bildirimler, ${total} okunmamış` : "Bildirimler"}
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" />
        </svg>
        {total > 0 && <span className="notification-count">{total > 99 ? "99+" : total}</span>}
      </button>

      {open && (
        <section className="notification-popover" aria-label="Bildirim listesi">
          <header><div><strong>Bildirimler</strong><span>{total} bekleyen bildirim</span></div></header>
          {error && <p className="notification-error" role="alert">{error}</p>}
          {loading ? (
            <p className="notification-state">Bildirimler yükleniyor…</p>
          ) : items.length === 0 ? (
            <p className="notification-state">Yeni bildiriminiz bulunmuyor.</p>
          ) : (
            <div className="notification-list">
              {items.map((item) => (
                <article
                  className={`notification-item${item.kind === "case.waiting_warning" ? " notification-warning" : ""}`}
                  key={item.id}
                >
                  <button
                    className="notification-main"
                    type="button"
                    disabled={busyId === item.id}
                    onClick={() => void dismiss(item, true)}
                  >
                    <strong>{item.title}</strong>
                    <span>{item.message}</span>
                    <time dateTime={item.created_at}>{formatNotificationDate(item.created_at)}</time>
                  </button>
                  <button
                    className="notification-dismiss"
                    type="button"
                    disabled={busyId === item.id}
                    onClick={() => void dismiss(item, false)}
                  >
                    Okundu
                  </button>
                </article>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
