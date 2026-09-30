import { useRef, useState } from "react";

import { useAuth } from "../../auth/AuthContext";
import { PasswordChangeDialog } from "./PasswordChangeDialog";

export function SecuritySettingsSection() {
  const { changePassword } = useAuth();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const openDialogButtonRef = useRef<HTMLButtonElement>(null);

  return (
    <section className="settings-panel" aria-labelledby="security-settings-title">
      <header className="settings-section-heading">
        <div>
          <p className="card-label">GÜVENLİK</p>
          <h2 id="security-settings-title">Parola güvenliği</h2>
          <p>Hesabınızın parolasını mevcut parolanızı doğrulayarak değiştirebilirsiniz.</p>
        </div>
      </header>

      {notice !== null && <div className="success-message" role="status">{notice}</div>}

      <div className="security-action-card">
        <div>
          <strong>Hesap parolası</strong>
          <span>Parolanız Firebase Authentication üzerinde güvenli biçimde saklanır.</span>
        </div>
        <button
          ref={openDialogButtonRef}
          type="button"
          className="primary-button compact-button"
          onClick={() => {
            setNotice(null);
            setDialogOpen(true);
          }}
        >
          Parolayı değiştir
        </button>
      </div>

      <div className="security-note">
        <strong>Güvenlik önerisi</strong>
        <p>Başka hesaplarda kullanmadığınız, tahmin edilmesi zor bir parola tercih edin.</p>
      </div>

      <PasswordChangeDialog
        open={dialogOpen}
        returnFocusRef={openDialogButtonRef}
        changePassword={changePassword}
        onClose={() => setDialogOpen(false)}
        onSuccess={() => setNotice("Parolanız başarıyla değiştirildi.")}
      />
    </section>
  );
}
