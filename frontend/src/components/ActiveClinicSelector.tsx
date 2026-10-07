import { useMemo, useState } from "react";

import { useAuth } from "../auth/AuthContext";

export function ActiveClinicSelector() {
  const { selectActiveClinic, user } = useAuth();
  const [saving, setSaving] = useState(false);

  const clinics = useMemo(() => {
    const unique = new Map<string, string>();
    for (const assignment of user?.clinic_roles ?? []) {
      if (assignment.role === "clinic_manager") {
        unique.set(assignment.clinic_id, assignment.clinic_name ?? "Klinik");
      }
    }
    return [...unique.entries()].sort((left, right) => left[1].localeCompare(right[1], "tr"));
  }, [user]);

  if (clinics.length < 2 || user === null || selectActiveClinic === undefined) {
    return null;
  }

  const selected = clinics.some(([id]) => id === user.preferences.active_clinic_id)
    ? user.preferences.active_clinic_id ?? ""
    : "";

  return (
    <label className="active-clinic-selector">
      <span>Aktif klinik</span>
      <select
        aria-label="Aktif klinik"
        value={selected}
        disabled={saving}
        onChange={(event) => {
          setSaving(true);
          void selectActiveClinic(event.target.value || null)
            .catch(() => undefined)
            .finally(() => setSaving(false));
        }}
      >
        <option value="">Tüm klinikler</option>
        {clinics.map(([id, name]) => <option key={id} value={id}>{name}</option>)}
      </select>
    </label>
  );
}
