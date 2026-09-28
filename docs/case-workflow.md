# DentalApp vaka iş akışı kararı

Bu belge, vaka tabloları ve API'leri oluşturulmadan önce uygulanacak MVP iş kurallarını
tek yerde sabitler. Çalışan karşılığı `backend/app/domain/case_workflow.py` dosyasındadır.

## Temel akış

`draft → manager_review → lab_design → dentist_review → ready_for_production →
in_production → production_completed → shipped → delivered`

Yönetici incelemesinde düzeltme istenirse vaka `manager_revision_requested` durumuna,
kesin ret verilirse `manager_rejected` durumuna geçer. Tasarım düzeltmesinde
`design_revision_requested` durumu kullanılır. İade teknisyen tarafından teslim
alındığında vaka `return_review` durumuna geçer. Yönetici hekim buradan
`reproduction_requested` veya `rescan_requested` kararı verir.

## Kesinleştirilen kurallar

- Yönetici onayı ve sorumlu hekim tasarım onayı atlanamaz.
- Klinik personeli hekim adına vaka açabilir; vaka üzerinde ayrıca bir
  `responsible_dentist_user_id` tutulur.
- Tasarım onayını yalnızca sorumlu hekim verir. Kaydı klinik personelinin açmış olması
  bu yetkiyi personele vermez.
- Yönetici hekim kendi açtığı veya sorumlu hekimi olduğu vakayı onaylayabilir. Bu durum
  `is_manager_self_approval` olarak audit kaydında işaretlenir.
- Yönetici onayı tarama sürümünü, hekim tasarım onayı tasarım sürümünü kilitler.
  Onay geri alınmaz; düzeltme yeni sürümle yapılır.
- Düzeltme, ret, iptal, iade ve iade sonrası karar işlemlerinde gerekçe zorunludur.
- Ürünü teknisyen kargoya verir. Şubeye teslimi klinik yöneticisi veya klinik
  personeli doğrular.
- İade sonrasında yeniden üretim aynı vaka içinde yeni üretim döngüsü olarak ilerler.
  Yeni tarama kararında vaka tekrar yönetici onayına gönderilir.
- Sistem yöneticisi kullanıcı ve şube yönetir; klinik onay rollerini devralmaz.

Bu aşamada veritabanına vaka tablosu eklenmemiştir. Sonraki aşamada model ve migration
bu durum makinesini kaynak kabul ederek hazırlanacaktır.

