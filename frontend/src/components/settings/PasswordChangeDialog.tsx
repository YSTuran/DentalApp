import {
  type FormEvent,
  type KeyboardEvent as ReactKeyboardEvent,
  type RefObject,
  useEffect,
  useRef,
  useState,
} from "react";

interface PasswordChangeDialogProps {
  open: boolean;
  returnFocusRef: RefObject<HTMLButtonElement | null>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  onClose: () => void;
  onSuccess: () => void;
}

export function PasswordChangeDialog({
  open,
  returnFocusRef,
  changePassword,
  onClose,
  onSuccess,
}: PasswordChangeDialogProps) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newPasswordAgain, setNewPasswordAgain] = useState("");
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPasswords, setShowNewPasswords] = useState(false);
  const [step, setStep] = useState<"form" | "confirmation">("form");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dialogRef = useRef<HTMLElement>(null);
  const currentPasswordRef = useRef<HTMLInputElement>(null);
  const confirmationBackRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const focusTimer = window.setTimeout(() => {
      if (step === "form") currentPasswordRef.current?.focus();
      else confirmationBackRef.current?.focus();
    }, 0);
    return () => window.clearTimeout(focusTimer);
  }, [open, step]);

  if (!open) return null;

  const passwordLongEnough = newPassword.length >= 8;
  const passwordsMatch = newPassword.length > 0 && newPassword === newPasswordAgain;
  const passwordChanged = newPassword.length > 0 && currentPassword !== newPassword;

  function resetAndClose() {
    if (submitting) return;
    setCurrentPassword("");
    setNewPassword("");
    setNewPasswordAgain("");
    setShowCurrentPassword(false);
    setShowNewPasswords(false);
    setStep("form");
    setError(null);
    onClose();
    window.setTimeout(() => returnFocusRef.current?.focus(), 0);
  }

  function requestConfirmation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!passwordLongEnough) {
      setError("Yeni parola en az 8 karakter olmalıdır.");
      return;
    }
    if (!passwordsMatch) {
      setError("Yeni parola ve tekrarı birbiriyle eşleşmiyor.");
      return;
    }
    if (!passwordChanged) {
      setError("Yeni parola eski paroladan farklı olmalıdır.");
      return;
    }
    setStep("confirmation");
  }

  async function confirmPasswordChange() {
    setSubmitting(true);
    setError(null);
    try {
      await changePassword(currentPassword, newPassword);
      setSubmitting(false);
      setCurrentPassword("");
      setNewPassword("");
      setNewPasswordAgain("");
      setStep("form");
      onClose();
      onSuccess();
      window.setTimeout(() => returnFocusRef.current?.focus(), 0);
    } catch (changeError) {
      setSubmitting(false);
      setStep("form");
      setError(
        changeError instanceof Error ? changeError.message : "Parola değiştirilemedi.",
      );
    }
  }

  function handleDialogKeyDown(event: ReactKeyboardEvent<HTMLElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      resetAndClose();
      return;
    }
    if (event.key !== "Tab") return;

    const focusableElements = dialogRef.current?.querySelectorAll<HTMLElement>(
      'button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])',
    );
    if (focusableElements === undefined || focusableElements.length === 0) return;

    const first = focusableElements[0];
    const last = focusableElements[focusableElements.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  return (
    <div
      className="modal-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) resetAndClose();
      }}
    >
      <section
        ref={dialogRef}
        className="modal-card password-dialog"
        role={step === "confirmation" ? "alertdialog" : "dialog"}
        aria-modal="true"
        aria-labelledby="password-dialog-title"
        aria-describedby="password-dialog-description"
        onKeyDown={handleDialogKeyDown}
      >
        {step === "form" ? (
          <>
            <div className="modal-heading">
              <div>
                <p className="eyebrow">GÜVENLİK</p>
                <h2 id="password-dialog-title">Parolayı değiştir</h2>
              </div>
              <button
                type="button"
                className="icon-button"
                onClick={resetAndClose}
                aria-label="Pencereyi kapat"
              >×</button>
            </div>
            <p id="password-dialog-description">
              Mevcut parolanız Firebase üzerinden doğrulanacaktır.
            </p>

            {error !== null && <div className="form-error" role="alert">{error}</div>}

            <form className="management-form password-dialog-form" onSubmit={requestConfirmation}>
              <label htmlFor="current-password">Eski parola</label>
              <div className="password-input-row">
                <input
                  ref={currentPasswordRef}
                  id="current-password"
                  type={showCurrentPassword ? "text" : "password"}
                  value={currentPassword}
                  onChange={(event) => setCurrentPassword(event.target.value)}
                  autoComplete="current-password"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowCurrentPassword((visible) => !visible)}
                  aria-label={showCurrentPassword ? "Eski parolayı gizle" : "Eski parolayı göster"}
                >{showCurrentPassword ? "Gizle" : "Göster"}</button>
              </div>

              <label htmlFor="new-password">Yeni parola</label>
              <div className="password-input-row">
                <input
                  id="new-password"
                  type={showNewPasswords ? "text" : "password"}
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                  autoComplete="new-password"
                  minLength={8}
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowNewPasswords((visible) => !visible)}
                  aria-label={showNewPasswords ? "Yeni parolaları gizle" : "Yeni parolaları göster"}
                >{showNewPasswords ? "Gizle" : "Göster"}</button>
              </div>

              <label htmlFor="new-password-again">Yeni parola tekrar</label>
              <input
                id="new-password-again"
                type={showNewPasswords ? "text" : "password"}
                value={newPasswordAgain}
                onChange={(event) => setNewPasswordAgain(event.target.value)}
                autoComplete="new-password"
                minLength={8}
                required
              />

              <ul className="password-requirements" aria-label="Parola koşulları">
                <li className={passwordLongEnough ? "met" : undefined}>En az 8 karakter</li>
                <li className={passwordChanged ? "met" : undefined}>Eski paroladan farklı</li>
                <li className={passwordsMatch ? "met" : undefined}>Parolalar eşleşiyor</li>
              </ul>

              <div className="modal-actions">
                <button type="button" className="secondary-button" onClick={resetAndClose}>
                  Vazgeç
                </button>
                <button className="primary-button compact-button">Devam et</button>
              </div>
            </form>
          </>
        ) : (
          <>
            <div className="modal-heading">
              <div>
                <p className="eyebrow">ONAY GEREKLİ</p>
                <h2 id="password-dialog-title">Parola değişikliğini onaylıyor musunuz?</h2>
              </div>
            </div>
            <p id="password-dialog-description">
              Yeni parolanız hemen geçerli olacaktır. Sonraki girişlerde yeni parolayı
              kullanmanız gerekir.
            </p>
            <div className="modal-actions">
              <button
                ref={confirmationBackRef}
                type="button"
                className="secondary-button"
                onClick={() => setStep("form")}
                disabled={submitting}
              >
                Düzenlemeye dön
              </button>
              <button
                type="button"
                className="primary-button compact-button"
                onClick={() => void confirmPasswordChange()}
                disabled={submitting}
              >
                {submitting ? "Değiştiriliyor…" : "Evet, değiştir"}
              </button>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
