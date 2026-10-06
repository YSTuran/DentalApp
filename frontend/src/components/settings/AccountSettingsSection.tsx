import { userRoleLabels } from "../../lib/role-format";
import type { CurrentUser } from "../../types/auth";

function initials(fullName: string): string {
  return fullName
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toLocaleUpperCase("tr-TR") ?? "")
    .join("");
}

function clinicScope(user: CurrentUser): string {
  if (user.global_roles.includes("system_admin")) return "Tüm klinikler";
  if (user.global_roles.includes("technician")) return "Laboratuvar geneli";

  const clinicCount = new Set(user.clinic_roles.map(({ clinic_id }) => clinic_id)).size;
  return clinicCount === 0 ? "Klinik ataması bulunmuyor" : `${clinicCount} klinik`;
}

interface AccountSettingsSectionProps {
  user: CurrentUser;
}

export function AccountSettingsSection({ user }: AccountSettingsSectionProps) {
  const roles = userRoleLabels(user);

  return (
    <section className="settings-panel" aria-labelledby="account-settings-title">
      <header className="settings-section-heading">
        <div>
          <p className="card-label">HESAP</p>
          <h2 id="account-settings-title">Hesap bilgileri</h2>
          <p>Kimlik ve yetki bilgileriniz sistem yöneticiniz tarafından yönetilir.</p>
        </div>
      </header>

      <div className="account-profile-summary">
        <div className="account-avatar" aria-hidden="true">{initials(user.full_name)}</div>
        <div>
          <strong>{user.full_name}</strong>
          <span>{user.email}</span>
        </div>
      </div>

      <dl className="settings-detail-list">
        <div><dt>Ad soyad</dt><dd>{user.full_name}</dd></div>
        <div><dt>E-posta</dt><dd>{user.email}</dd></div>
        <div>
          <dt>Roller</dt>
          <dd className="settings-role-list">
            {roles.map((role) => <span key={role}>{role}</span>)}
          </dd>
        </div>
        <div><dt>Klinik kapsamı</dt><dd>{clinicScope(user)}</dd></div>
      </dl>
    </section>
  );
}
