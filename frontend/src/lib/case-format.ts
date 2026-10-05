import type { CaseStatus, MeshStatus } from "../types/case";

export const caseStatusLabels: Record<CaseStatus, string> = {
  draft: "Taslak",
  manager_review: "Yönetici onayında",
  manager_revision_requested: "Klinik düzeltmesi istendi",
  manager_rejected: "Kesin reddedildi",
  lab_design: "Laboratuvar tasarımında",
  dentist_review: "Hekim tasarım onayında",
  design_revision_requested: "Tasarım düzeltmesi istendi",
  ready_for_production: "Üretime hazır",
  in_production: "Üretimde",
  production_completed: "Üretim tamamlandı",
  shipped: "Kargoya verildi",
  delivered: "Şubeye teslim edildi",
  return_review: "İade değerlendirmesinde",
  reproduction_requested: "Yeniden üretim istendi",
  rescan_requested: "Yeni tarama istendi",
  cancelled: "İptal edildi",
};

export const meshStatusLabels: Record<MeshStatus, string> = {
  pending: "Doğrulanıyor",
  valid: "Geçerli mesh",
  invalid: "Mesh sorunlu",
  failed: "Doğrulama başarısız",
};

export const caseActionLabels: Record<string, string> = {
  create: "Vaka oluşturuldu",
  submit: "Yönetici onayına gönderildi",
  cancel: "Vaka iptal edildi",
  manager_approve: "Tarama onaylandı",
  manager_request_revision: "Tarama düzeltmesi istendi",
  manager_reject: "Vaka kesin reddedildi",
  upload_design: "Tasarım hekim onayına gönderildi",
  dentist_approve_design: "Tasarım onaylandı",
  dentist_request_design_revision: "Tasarım düzeltmesi istendi",
  start_production: "Üretim başlatıldı",
  complete_production: "Üretim tamamlandı",
  ship: "Kargoya verildi",
  confirm_delivery: "Şube teslimi doğrulandı",
  register_return_received: "İade laboratuvara ulaştı",
  decide_reproduction: "Yeniden üretim kararı verildi",
  decide_rescan: "Yeni tarama kararı verildi",
};

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
}
