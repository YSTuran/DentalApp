export type AuditTone =
  | "session"
  | "security"
  | "clinic"
  | "user"
  | "role"
  | "case"
  | "production"
  | "delivery"
  | "system";

export const AUDIT_LEGEND: Array<{ tone: AuditTone; label: string }> = [
  { tone: "session", label: "Oturum" },
  { tone: "security", label: "Hesap güvenliği" },
  { tone: "clinic", label: "Klinik" },
  { tone: "user", label: "Kullanıcı" },
  { tone: "role", label: "Rol ve yetki" },
];

export function auditToneFor(action: string, entityType: string): AuditTone {
  if (action.startsWith("auth.")) return "session";
  if (action.startsWith("account.") || action.startsWith("security.")) return "security";
  if (action.startsWith("clinic.") || entityType === "clinic") return "clinic";
  if (action.startsWith("user.role_") || entityType === "user_role_assignment") return "role";
  if (action.startsWith("user.") || entityType === "user") return "user";
  if (
    action.startsWith("case.") ||
    action.startsWith("scan.") ||
    action.startsWith("design.") ||
    action.startsWith("approval.")
  ) return "case";
  if (
    action.startsWith("production.") ||
    action.startsWith("laboratory.") ||
    action.startsWith("material.")
  ) return "production";
  if (
    action.startsWith("shipment.") ||
    action.startsWith("delivery.") ||
    action.startsWith("return.")
  ) return "delivery";
  return "system";
}
