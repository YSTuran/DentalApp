import { type FormEvent, useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { DemoBanner } from "../components/DemoBanner";
import { useTheme } from "../theme/ThemeContext";
import { COLOR_PALETTE_OPTIONS, THEME_MODE_OPTIONS } from "../theme/options";
import type { ThemePreferenceUpdate } from "../types/theme";

export function SettingsPage() {
  const { user, logout, changePassword } = useAuth();
  const { preferences, resolvedMode, updatePreferences } = useTheme();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newPasswordAgain, setNewPasswordAgain] = useState("");
  const [confirmationOpen, setConfirmationOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [themeSaving, setThemeSaving] = useState(false);
  const [themeError, setThemeError] = useState<string | null>(null);
  const [themeNotice, setThemeNotice] = useState<string | null>(null);

  if (user === null) return null;

  function requestConfirmation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setNotice(null);

    if (newPassword.length < 8) {
      setError("Yeni parola en az 8 karakter olmalıdır.");
      return;
    }
    if (newPassword !== newPasswordAgain) {
      setError("Yeni parola ve tekrarı birbiriyle eşleşmiyor.");
      return;
    }
    if (currentPassword === newPassword) {
      setError("Yeni parola eski paroladan farklı olmalıdır.");
      return;
    }
    setConfirmationOpen(true);
  }

  async function confirmPasswordChange() {
    setSubmitting(true);
    setError(null);
    try {
      await changePassword(currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setNewPasswordAgain("");
      setConfirmationOpen(false);
      setNotice("Parolanız başarıyla değiştirildi.");
    } catch (changeError) {
      setConfirmationOpen(false);
      setError(
        changeError instanceof Error ? changeError.message : "Parola değiştirilemedi.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function changeAppearance(update: ThemePreferenceUpdate) {
    setThemeSaving(true);
    setThemeError(null);
    setThemeNotice(null);
    try {
      await updatePreferences(update);
      setThemeNotice("Görünüm tercihiniz kaydedildi.");
    } catch {
      setThemeError("Görünüm tercihi kaydedilemedi. Önceki seçiminiz geri yüklendi.");
    } finally {
      setThemeSaving(false);
    }
  }

  return (
    <div className="dashboard-shell">
      <DemoBanner />
      <header className="topbar">
        <Link className="brand-inline brand-link" to="/">
          <div className="brand-mark brand-mark-small" aria-hidden="true">D</div>
          <div><strong>DentalApp</strong><span>Hesap ayarları</span></div>
        </Link>
        <div className="topbar-actions">
          <Link className="text-link" to="/">Panele dön</Link>
          <button className="secondary-button" onClick={() => void logout()}>Çıkış yap</button>
        </div>
      </header>

      <main className="settings-content">
        <div className="page-heading settings-heading">
          <div>
            <p className="eyebrow">HESABIM</p>
            <h1>Ayarlar</h1>
            <p>Kişisel hesap güvenliği ve görünüm ayarlarınızı yönetin.</p>
          </div>
        </div>

        <div className="settings-grid">
          <section className="settings-card account-summary">
            <p className="card-label">HESAP BİLGİLERİ</p>
            <dl>
              <div><dt>Ad soyad</dt><dd>{user.full_name}</dd></div>
              <div><dt>E-posta</dt><dd>{user.email}</dd></div>
            </dl>
          </section>

          <section className="settings-card theme-card">
            <div className="theme-card-heading">
              <div>
                <p className="card-label">GÖRÜNÜM</p>
                <h2>Tema tercihi</h2>
                <p>Görünüm cihazda hemen uygulanır ve hesabınızla eşitlenir.</p>
              </div>
              <span className="resolved-theme-badge">
                Şu anda {resolvedMode === "dark" ? "karanlık" : "açık"}
              </span>
            </div>

            {themeNotice !== null && (
              <div className="success-message" role="status">{themeNotice}</div>
            )}
            {themeError !== null && (
              <div className="form-error" role="alert">{themeError}</div>
            )}

            <div className="theme-settings-grid">
              <fieldset className="theme-options" disabled={themeSaving}>
                <legend>Görünüm modu</legend>
                <div className="theme-choice-grid mode-choice-grid">
                  {THEME_MODE_OPTIONS.map((option) => (
                    <label className="theme-choice" key={option.value}>
                      <input
                        type="radio"
                        name="theme-mode"
                        value={option.value}
                        checked={preferences.theme_mode === option.value}
                        onChange={() => void changeAppearance({ theme_mode: option.value })}
                      />
                      <span className={`mode-preview mode-preview-${option.value}`} aria-hidden="true">
                        <i />
                      </span>
                      <strong>{option.label}</strong>
                      <small>{option.description}</small>
                    </label>
                  ))}
                </div>
              </fieldset>

              <fieldset className="theme-options" disabled={themeSaving}>
                <legend>Renk paleti</legend>
                <div className="theme-choice-grid palette-choice-grid">
                  {COLOR_PALETTE_OPTIONS.map((option) => (
                    <label className="theme-choice palette-choice" key={option.value}>
                      <input
                        type="radio"
                        name="color-palette"
                        value={option.value}
                        checked={preferences.color_palette === option.value}
                        onChange={() => void changeAppearance({ color_palette: option.value })}
                      />
                      <span className={`palette-swatch palette-swatch-${option.value}`} aria-hidden="true">
                        <i /><i /><i />
                      </span>
                      <strong>{option.label}</strong>
                      <small>{option.description}</small>
                    </label>
                  ))}
                </div>
              </fieldset>
            </div>
          </section>

          <section className="settings-card password-card">
            <p className="card-label">PAROLA GÜVENLİĞİ</p>
            <h2>Parolayı değiştir</h2>
            <p>İşlemi tamamlamak için mevcut parolanız Firebase üzerinden doğrulanır.</p>

            {notice !== null && <div className="success-message" role="status">{notice}</div>}
            {error !== null && <div className="form-error" role="alert">{error}</div>}

            <form className="management-form password-form" onSubmit={requestConfirmation}>
              <label>Eski parola
                <input type="password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} autoComplete="current-password" required />
              </label>
              <label>Yeni parola
                <input type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} autoComplete="new-password" minLength={8} required />
              </label>
              <label>Yeni parola tekrar
                <input type="password" value={newPasswordAgain} onChange={(event) => setNewPasswordAgain(event.target.value)} autoComplete="new-password" minLength={8} required />
              </label>
              <div className="settings-actions">
                <button className="primary-button compact-button" disabled={submitting}>Parolayı değiştir</button>
              </div>
            </form>
          </section>
        </div>
      </main>

      {confirmationOpen && (
        <div className="modal-backdrop" role="presentation">
          <section className="modal-card modal-card-small confirmation-dialog" role="alertdialog" aria-modal="true" aria-labelledby="password-confirm-title" aria-describedby="password-confirm-description">
            <div className="modal-heading">
              <div><p className="eyebrow">ONAY GEREKLİ</p><h2 id="password-confirm-title">Parola değişikliğini onaylıyor musunuz?</h2></div>
              <button className="icon-button" onClick={() => setConfirmationOpen(false)} aria-label="Pencereyi kapat">×</button>
            </div>
            <p id="password-confirm-description">Yeni parolanız hemen geçerli olacaktır. Bundan sonraki girişlerde yeni parolayı kullanmanız gerekir.</p>
            <div className="modal-actions">
              <button className="secondary-button" onClick={() => setConfirmationOpen(false)} disabled={submitting}>Vazgeç</button>
              <button className="primary-button compact-button" onClick={() => void confirmPasswordChange()} disabled={submitting}>{submitting ? "Değiştiriliyor…" : "Evet, değiştir"}</button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
