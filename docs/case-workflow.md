# DentalApp vaka iş akışı kararı

Bu belge, uygulanmış MVP vaka iş kurallarını tek yerde açıklar. Durum makinesinin
çalışan karşılığı `backend/app/domain/case_workflow.py`; kalıcı veri yapıları ise
`backend/app/models/case.py` dosyasındadır.

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
- Durum değişiklikleri ilgili yönetici hekim, sorumlu hekim, klinik personeli veya
  teknisyenlere uygulama içi bildirim üretir. Bildirimlerde hasta adı bulunmaz.
- Bildirimler ayrıca tekrar denemeli e-posta kuyruğuna yazılır; SMTP gönderimi API
  isteğini bekletmez ve e-posta içeriğinde hasta bilgisi bulunmaz.
- Hasta adı ve hasta kodu veritabanında AES-256-GCM ile şifreli tutulur. Hasta kodu
  araması HMAC kör indeksiyle yalnızca tam eşleşme üzerinden yapılır. Audit olayları
  bu değerlerin kendisini değil, ilgili alanların değiştiği bilgisini saklar.
- Aktif bir aşamanın bekleme eşiği aşıldığında son durum geçmişi esas alınarak ilgili
  role tekil bir uyarı oluşturulur.
- Bildirimi okundu olarak işaretlemek veya bağlı vaka sayfasını açmak bildirimi aktif
  listeden kaldırır; kayıt veritabanından silinmez.

Vaka, dosya sürümü, onay ve durum geçmişi tabloları migration ile oluşturulmuştur.
Onaylanan dosya sürümlerinin kilidi veritabanı trigger'ıyla korunur; onay ve geçmiş
kayıtları deterministik sıra numarasıyla okunur.

