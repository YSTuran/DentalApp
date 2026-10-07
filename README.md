# DentalApp

Diş klinikleri ile laboratuvar arasındaki vaka, tasarım, onay, üretim ve teslim süreçlerini yöneten demo uygulaması.

> DEMO — Gerçek hasta verisi girmeyiniz.

## Uygulanan MVP

- FastAPI uygulama fabrikası
- Ortam değişkeni tabanlı yapılandırma
- PostgreSQL için SQLAlchemy bağlantı katmanı
- Redis ve Celery bağlantı katmanı
- Alembic migration altyapısı
- Firebase Authentication ve yerel Authentication Emulator desteği
- Klinik kapsamlı rol/yetki kontrol katmanı
- PostgreSQL seviyesinde değiştirilemez audit kayıtları
- Parçalı, devam ettirilebilir ve SHA-256 kontrollü STL yükleme altyapısı
- Redis/Celery tabanlı asenkron STL mesh doğrulaması
- Sistem yöneticisi için yönetim, klinik yöneticisi için klinik kapsamlı salt okunur ekranlar
- Firebase ile PostgreSQL'i birlikte yöneten kullanıcı ve rol API'si
- Liveness ve readiness endpoint'leri
- Pytest başlangıç testleri
- Kullanıcıya özel uygulama içi bildirim merkezi
- Filtrelenmiş ve kategori renkli audit PDF çıktısı
- AES-256-GCM ile uygulama katmanında şifrelenen hasta adı ve hasta kodu
- Rol ile klinik atamasını ayıran çoklu şube yetkilendirmesi
- Hedef hekimin kabul/ret kararıyla tamamlanan, değiştirilemez vaka devri
- Yetki kapsamlı operasyon raporları ve hasta bilgisi içermeyen PDF çıktısı

## Yerel kurulum (PowerShell)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.lock
python -m pip install -e . --no-deps
uvicorn app.main:app --reload
```

`backend/requirements.lock` Windows geliştirme ortamı için üretilmiştir. Ubuntu üzerinde
çalışan GitHub Actions, platforma özel bağımlılıkları ayırmak için
`backend/requirements-linux.lock` dosyasını kullanır. Linux kilidini güncellemek için proje
kökünde şu komut çalıştırılabilir:

```powershell
docker run --rm -v "${PWD}:/workspace" -w /workspace python:3.13-slim sh -lc "python -m pip install pip-tools==7.6.1 && python -m piptools compile --extra=dev --output-file=backend/requirements-linux.lock backend/pyproject.toml"
```

Yerel ayarlar doğrudan `backend/.env` dosyasından okunur. Bu dosya veritabanı
parolası ve uygulama anahtarı içerebildiği için Git'e eklenmez.

Uygulama: `http://127.0.0.1:8000`

API belgeleri: `http://127.0.0.1:8000/docs`

Sağlık kontrolleri:

- `GET /api/health/live`: API sürecinin çalıştığını gösterir.
- `GET /api/health`: PostgreSQL, Redis, Firebase ve Celery worker/beat kalp atışını
  kontrol eder. Servisler ilk açıldığında kalp atışının oluşması 15 saniye sürebilir.

## Firebase Authentication Emulator

Proje kökünde ayrı bir terminal açın:

```powershell
npx firebase emulators:start --only auth
```

- Emulator UI: `http://127.0.0.1:4000`
- Authentication Emulator: `http://127.0.0.1:9099`

İlk sistem yöneticisini emulator çalışırken oluşturmak için:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m app.cli.create_admin
```

Aynı komut farklı bir e-posta ile tekrar çalıştırılarak kontrollü biçimde ikinci
bir sistem yöneticisi oluşturulabilir. Mevcut ve aktif bir yöneticinin yerel emulator
parolası unutulursa şu kurtarma komutu kullanılır:

```powershell
python -m app.cli.create_admin --email admin@example.test --reset-password
```

Parola sıfırlama seçeneği güvenlik nedeniyle gerçek Firebase ortamında çalışmaz.

Emulator verileri ilk kez kaydedilecekse emulator açıkken başka bir terminalde:

```powershell
npx firebase emulators:export .\firebase-export --only auth --force
```

Sonraki çalıştırmalarda kayıtlı kullanıcıları yüklemek ve kapanışta tekrar kaydetmek için:

```powershell
npx firebase emulators:start --only auth --import=.\firebase-export --export-on-exit
```

PostgreSQL'deki sistem yöneticisi duruyor ancak emulator kullanıcısı silinmişse
`python -m app.cli.create_admin` komutunu tekrar çalıştırın. Komut mevcut kaydın
`firebase_uid` değerini koruyarak emulator hesabını yeniden oluşturur.

Authentication endpoint'leri:

- `GET /api/auth/csrf`
- `POST /api/auth/session`
- `GET /api/auth/me`
- `POST /api/auth/logout`

Başarılı oturum açma ve kapatma işlemleri audit kaydı oluşturur.

## Audit ve yetkilendirme

Audit kayıtları yalnızca eklenebilir; PostgreSQL trigger'ı `UPDATE`, `DELETE` ve
`TRUNCATE` işlemlerini reddeder. Global audit listesini yalnızca `system_admin`
rolü görüntüleyebilir:

- `GET /api/audit-events`

Endpoint; `action`, `entity_type`, `entity_id`, `actor_user_id`, `clinic_id`,
`created_from` ve `created_before` filtreleri ile `limit`/`offset` sayfalamasını
destekler. Audit ekranındaki filtreler otomatik uygulanır. **PDF olarak yazdır**
düğmesi aktif filtrelerle eşleşen bütün kayıtları kategori renklerini koruyan kutulu
bir rapora dönüştürür. Açılan sistem penceresinde **PDF olarak kaydet** seçilebilir.

## Bildirimler

Oturum açmış bütün kullanıcılar sayfa başlıklarındaki çan düğmesinden kendilerine
ait bekleyen bildirimleri görüntüleyebilir:

- `GET /api/notifications`: kullanıcının kapatılmamış bildirimleri.
- `POST /api/notifications/{notification_id}/dismiss`: bildirimi okundu olarak kapatır.

Vaka onaya gönderildiğinde, düzeltme veya ret kararı verildiğinde, tasarım onayı
gerektiğinde, ürün kargoya verildiğinde ve iade kararı oluştuğunda ilgili role bildirim
üretilir. Metinlerde hasta adı kullanılmaz. Bildirime tıklamak ilgili vaka ekranına
götürür ve bildirimi kapatır. **Okundu** düğmesi de bildirimi listeden kaldırır; kayıt
fiziksel olarak silinmez, `dismissed_at` zamanı ile saklanır.

Her uygulama içi bildirim aynı transaction içinde `email_outbox` kuyruğuna da eklenir.
Celery worker e-postaları SMTP üzerinden gönderir; geçici hatalarda artan aralıklarla
yeniden dener ve gönderim sonucunu saklar. Yerel geliştirmede `npm run dev`, Mailpit'i
Docker ile başlatır ve terminalde test gelen kutusunu gösterir:

- Mailpit gelen kutusu: `http://localhost:8025`
- Yerel SMTP: `127.0.0.1:1025`

Uydurma `.test` ve `.invalid` adreslerine gönderilen e-postalar internete çıkmadan bu
kutuda görüntülenir. E-posta metinlerinde hasta adı veya klinik serbest notları yoktur.
Gerçek ortamda `SMTP_HOST`, `SMTP_PORT`, `SMTP_STARTTLS`, `SMTP_USERNAME`,
`SMTP_PASSWORD`, `EMAIL_FROM_ADDRESS` ve `FRONTEND_BASE_URL` ayarları gerçek servisle
değiştirilir.

Celery Beat ayrıca aktif vakaların son durum geçmişini kontrol eder. Yapılandırılmış
süreyi aşan aşamalar için ilgili role bir kez çan bildirimi ve e-posta oluşturulur.
Tekrarlar `case_wait_alerts` tablosundaki vaka, aşama başlangıcı ve alıcı birleşimiyle
engellenir. Varsayılan süreler `CASE_WAIT_WARNING_HOURS` ortam değişkenine JSON nesnesi
verilerek değiştirilebilir.

Backend yetki katmanı global rol, herhangi bir rol, klinik erişimi ve klinik rolü
kontrollerini ayrı ayrı uygular. Sistem yöneticisi klinik rolü gerektiren işlemleri
yalnızca ilgili kontrol açıkça izin veriyorsa devralabilir.

## Hasta kimlik bilgilerinin korunması

Hasta adı, hasta kodu, diş numaraları, özel ve dinamik vaka alanları, özgün dosya
adları, onay/ret/düzeltme gerekçeleri ile üretim, teslim ve iade serbest notları
PostgreSQL'de açık metin olarak tutulmaz. FastAPI bu alanları AES-256-GCM ile tablo ve
alan bağlamına bağlı biçimde şifreler; yetki kontrolü sonrasında yalnızca gerekli alanı
çözer. Teknisyen hasta kodunu görebilir ancak hasta adını, klinik serbest notlarını veya
bu bilgileri içerebilecek geçmiş gerekçelerini göremez. Sistem yöneticisi de yalnızca
global yönetici olduğu için hasta adına erişemez.

Hasta kodu araması, ayrı bir 256 bit anahtarla oluşturulan HMAC kör indeksi üzerinden
tam eşleşmeyle yapılır. Vaka numarası kısmi aranabilir; hasta kodunun tamamı girilmelidir.
Audit kayıtlarında hasta adı, hasta kodu, özel not veya dinamik alan değerleri tekrar
saklanmaz; yalnızca alanın değiştiği ve değer bulunup bulunmadığı kaydedilir. API
yanıtları varsayılan olarak `Cache-Control: no-store` başlığı taşır.

Yerel anahtarlar Git'e eklenmeyen `backend/.env` içindeki
`PATIENT_DATA_KEYS`, `PATIENT_DATA_ACTIVE_KEY_ID` ve `PATIENT_LOOKUP_KEY`
ayarlarından okunur. Şifreleme anahtarı ile arama anahtarı birbirinden farklıdır.
Anahtar sürümü şifreli kayıtla birlikte tutulduğu için yeni yazmalar farklı bir anahtar
sürümüne geçirilebilir.

Veritabanı yedeği şifreli sütunları içerir ancak anahtarları içermez. Bu üç ayar,
veritabanı yedeğinden ayrı ve erişimi kısıtlı bir parola kasasında ayrıca yedeklenmelidir.
Anahtarlar kaybolursa hasta adı ve kodu geri getirilemez. Anahtar değerleri uygulama
loglarına, audit kayıtlarına veya hata yanıtlarına yazdırılmamalıdır.

## Klinik API

- `GET /api/clinics`: sistem yöneticisi tüm klinikleri, klinik yöneticisi yalnızca
  aktif klinik ataması bulunan klinikleri görür.
- `GET /api/clinics/{clinic_id}`: sistem yöneticisi veya ilgili kliniğin yöneticisi.
- `POST /api/clinics`: yalnızca sistem yöneticisi.
- `PATCH /api/clinics/{clinic_id}`: yalnızca sistem yöneticisi.
- `POST /api/clinics/{clinic_id}/deactivate`: yalnızca sistem yöneticisi, gerekçe zorunlu.
- `POST /api/clinics/{clinic_id}/reactivate`: yalnızca sistem yöneticisi, gerekçe zorunlu.

Klinik silme endpoint'i yoktur. Yazma işlemleri CSRF korumalıdır ve klinik değişikliği
ile `clinic.created`, `clinic.updated`, `clinic.deactivated` veya `clinic.reactivated`
audit olayı aynı PostgreSQL transaction'ında kaydedilir.

Sistem yöneticisi giriş yaptıktan sonra klinik yönetimi ekranına
`http://localhost:5173/yonetim/klinikler` adresinden ulaşabilir. Burada arama,
aktif/pasif filtreleme, sayfalama, klinik ekleme, düzenleme ve gerekçeli durum
değişikliği yapılabilir. Klinik yöneticisi aynı ekranda yalnızca aktif rolünün
bulunduğu klinikleri ve kullanıcı ekranında bu kliniklerin hekimlerini salt okunur
görür. Kullanıcının mesleki rolü klinik atamalarından ayrı tutulur; bir kullanıcının
aynı anda yalnızca bir aktif rolü, fakat birden fazla aktif çalışma kliniği olabilir.
Rol değiştirmek klinik geçmişini silmez ve klinik atamasını değiştirmek rolü etkilemez.
Birden fazla kliniğe atanmış kullanıcı üst menüden aktif kliniği veya tüm yetkili
klinikleri seçebilir. Tercih kullanıcı hesabında saklanır ve vaka, klinik, kullanıcı
ve rapor ekranlarına uygulanır. Her vaka kendi `clinic_id` değeriyle birlikte vakayı
açan kullanıcıyı ve sorumlu hekimi ayrıca sakladığı için hekimin klinik ataması daha
sonra değişse bile işlem geçmişi bozulmaz.

Frontend sistem yönetimi ekranları:

- `http://localhost:5173/yonetim/klinikler`: klinik yönetimi.
- `http://localhost:5173/yonetim/kullanicilar`: personel hesabı oluşturma,
  kullanıcı/rol görüntüleme ve kullanıcıyı pasifleştirme veya etkinleştirme.
- `http://localhost:5173/yonetim/audit-kayitlari`: işlem, kayıt türü, klinik, tarih ve
  kayıt kimliğine göre filtrelenebilen, PDF çıktısı alınabilen değiştirilemez kayıtlar.
- `http://localhost:5173/ayarlar`: bütün kullanıcıların mevcut parolalarını
  doğrulayarak kendi Firebase parolalarını değiştirebildiği ve görünüm temasını
  seçebildiği hesap ayarları.

Yeni kullanıcı oluşturulduğunda Firebase geçici parolası ekranda yalnızca bir kez
gösterilir. Pencere kapatılmadan önce parola güvenli biçimde kaydedilip kullanıcıya
iletilmelidir.

Giriş ekranındaki **Oturumu açık tut** seçeneği işaretlenirse Firebase tarayıcı
oturumu ve FastAPI HttpOnly oturum çerezi kalıcı oluşturulur. Seçenek işaretlenmezse
oturum çerezi tarayıcı oturumu sona erdiğinde silinir. Normal kullanıcı yönetimi API'si
üzerinden `system_admin` rolü oluşturulamaz veya atanamaz; ilk sistem yöneticisi CLI
kurulum akışıyla yönetilir.

## Kullanıcı ve rol API'si

- `GET /api/users`: sistem yöneticisi tüm kullanıcıları görür. Klinik yöneticisi
  yalnızca sorumlu olduğu kliniklerdeki hekim ve yönetici hekimleri görür; diğer
  kliniklere ait rol atamaları yanıtta gösterilmez.
- `GET /api/users/{user_id}`: aynı görünürlük kurallarıyla kullanıcı detayı.
- `POST /api/users`: Firebase hesabını, PostgreSQL kullanıcısını, ilk rolü ve başlangıç
  klinik atamalarını oluşturur.
- `PATCH /api/users/{user_id}`: ad-soyad bilgisini Firebase ve PostgreSQL'de günceller.
- `POST /api/users/{user_id}/deactivate` ve `reactivate`: hesabı iki sistemde birlikte
  pasifleştirir veya etkinleştirir; gerekçe zorunludur.
- `POST /api/users/{user_id}/roles`: aktif rolü bulunmayan kullanıcıya yeni rol atar.
- `PATCH /api/users/{user_id}/roles/{assignment_id}`: aktif rolü değiştirir; eski atama
  silinmeden pasif tutulur ve gerekçe audit kaydına yazılır.
- `POST /api/users/{user_id}/roles/{assignment_id}/deactivate` ve `reactivate`:
  rol atamasının durumunu değiştirir; gerekçe zorunludur.
- `POST /api/users/{user_id}/clinics`: rolü değiştirmeden çalışma kliniği ekler.
- `POST /api/users/{user_id}/clinics/{assignment_id}/deactivate` ve `reactivate`:
  klinik atamasının durumunu değiştirir; gerekçe zorunludur.

Kullanıcı silme endpoint'i yoktur. Kullanıcı oluşturmada üretilen geçici parola
yalnızca başarılı `POST /api/users` yanıtında bir kez döner ve audit kaydına yazılmaz.
Firebase işlemi sonrasında PostgreSQL/audit işlemi başarısız olursa yapılan Firebase
değişikliği telafi edilir. Son aktif sistem yöneticisi veya oturumdaki yöneticinin
kendi hesabı pasifleştirilemez.

## Kullanıcı görünüm tercihleri

Kullanıcılar açık, karanlık veya cihaz ayarını izleyen sistem modunu; ayrıca
Dental yeşili, okyanus mavisi, menekşe, Arktik laboratuvar, adaçayı, grafit,
kehribar, bordo, mercan, kum ve sepya veya yüksek kontrast paletini seçebilir:

- `GET /api/account/preferences`: oturumdaki kullanıcının görünüm tercihleri.
- `PATCH /api/account/preferences`: CSRF korumalı tercih güncellemesi.

Tercihler PostgreSQL'deki `user_preferences` tablosunda saklanır ve değişiklikler
`user.preferences.updated` audit olayı üretir. Her oturumda yalnızca giriş yapan
kullanıcının PostgreSQL'deki hesap tercihi uygulanır; kullanıcılar arasında ortak
tema önbelleği kullanılmaz. Yeni hesapların varsayılanı açık mod ve Dental yeşili
paletidir. Giriş ekranı ise hesap tercihlerinden bağımsız, sabit açık Dental
temasında gösterilir.

## Frontend

Firebase Emulator, FastAPI ve React geliştirme sunucusunu birlikte başlatmak için
proje kökünde:

```powershell
npm run dev
```

Loglar aynı terminalde `FIREBASE`, `MAIL`, `API`, `WORKER`, `MESH`, `BEAT` ve `WEB` etiketleriyle
gösterilir. `Ctrl+C` servisleri kapatır; Firebase kullanıcıları temiz kapanışta
`firebase-export` klasörüne kaydedilir. PostgreSQL servisinin ve Redis konteynerinin
önceden çalışıyor olması gerekir.

`MESH` yalnızca kaynak yoğun STL doğrulamalarını, `WORKER` ise e-posta ve bakım gibi
kısa görevleri yürütür. Böylece büyük bir STL bildirimi ve e-posta gönderimini
bekletmez. `BEAT`, Redis geçici olarak ulaşılamazken kuyruğa alınamayan doğrulamaları
yeniden bulur ve süresi geçen yarım yüklemeleri, veritabanı kayıtlarını silmeden
`expired` durumuna geçirerek temizler. Beat ayrıca e-posta kuyruğunu ve vaka bekleme
sürelerini düzenli aralıklarla tarar.

Teknisyen, üretim iş emrindeki **Etiket yazdır** düğmesiyle 100 × 50 mm Code 128 vaka
etiketi oluşturabilir. Etiket vaka ve iş emri numarası, klinik, aparey, malzeme ve
üretim denemesini içerir; hasta adı ve hasta kodu etikete yazılmaz.

Yalnızca React, TypeScript ve Vite tabanlı frontend'i çalıştırmak için:

```powershell
cd frontend
npm install
npm run dev
```

Uygulamayı `http://localhost:5173` adresinden açın. Geliştirme ortamı ayarları
`frontend/.env` dosyasından okunur. Projede backend ve frontend için birer yerel
`.env` dosyası bulunur; bu dosyalar Git'e eklenmez. Firebase servis hesabı dosyası
frontend'e eklenmez.

Giriş sırasında Firebase Auth Emulator'dan alınan ID token FastAPI'ye gönderilir.
FastAPI doğrulamadan sonra CSRF korumalı, HttpOnly bir oturum çerezi üretir.

## Test

PostgreSQL çalışırken backend birim ve entegrasyon testleri ile frontend bileşen
testlerini birlikte çalıştırmak için
proje kökünde:

```powershell
npm test
```

Veritabanı gerektirmeyen hızlı testleri çalıştırmak için:

```powershell
npm run test:quick
```

Kod kalitesi ve üretim derlemesi kontrolleri `npm run lint` ve `npm run build`
komutlarıyla çalıştırılır. CI, Authentication Emulator'ı geçici olarak başlatıp
Firebase–PostgreSQL eşgüdüm testlerini de çalıştırır; bu nedenle emülatör testleri
otomatik doğrulamada atlanmaz.

Firebase Emulator testini de içeren yerel tam kontrol, geliştirme servisleri kapalıyken
`npm run verify:full` ile çalıştırılır. Bu komut emülatörü geçici olarak açıp kapatır.

## Vaka iş akışı

MVP vaka durumları, rol yetkileri, iki zorunlu onay, sorumlu hekim kuralı ve iade
kararları `docs/case-workflow.md` belgesinde tanımlanmıştır. Bu kuralların çalışan
karşılığı `backend/app/domain/case_workflow.py` dosyasıdır.

Temel vaka endpoint'leri:

- `GET /api/cases`: kullanıcının rolüne ve klinik kapsamına göre vaka listesi.
- `POST /api/cases`: klinik personeli, hekim veya yönetici hekim için taslak oluşturma.
- `GET /api/cases/{case_id}`: yetki kapsamındaki vaka detayı.
- `PATCH /api/cases/{case_id}`: taslak/düzeltme aşamasındaki vakayı güncelleme.
- `POST /api/cases/{case_id}/submit`: zorunlu alanları ve doğrulanmış tarama sürümünü
  kontrol ederek vakayı yönetici onayına gönderme.
- `POST /api/cases/{case_id}/manager-decision`: yönetici hekimin en son tarama
  sürümünü onaylaması, düzeltme istemesi veya kesin reddetmesi. Karar değiştirilemez
  onay kaydına bağlanır; onaylanan STL sürümü kilitlenir ve kendi vakasını onaylayan
  yönetici ayrıca işaretlenir.
- `POST /api/cases/{case_id}/cancel`: gerekçeli iptal; kayıt silinmez.
- `GET /api/cases/{case_id}/history`: değiştirilemez durum geçmişi.

İade kararı `reproduction` olduğunda teslim edilmiş eski vaka yeniden açılmaz.
Sistem, eski vakaya bağlı yeni bir `draft` vaka üretir; klinik, sorumlu hekim ve
şifreli hasta alanları güvenli biçimde aktarılır. STL/tasarım dosyaları ve onaylar
kopyalanmaz. Böylece yeni vaka yeniden tarama yükleme, yönetici onayı ve sorumlu hekim
tasarım onayından geçmeden üretime alınamaz. Eski ve yeni vaka numaraları detay ve
operasyon geçmişi ekranlarında birbirine bağlı gösterilir.

Vaka devri endpoint'leri:

- `GET /api/cases/{case_id}/transfer-options`: aynı klinikteki uygun hedef hekimler.
- `GET /api/cases/{case_id}/transfers`: vakanın silinmeyen devir geçmişi.
- `POST /api/cases/{case_id}/transfers`: klinik yöneticisi veya yönetici hekimin
  gerekçeli devir talebi oluşturması.
- `POST /api/cases/{case_id}/transfers/{transfer_id}/decision`: yalnızca hedef
  hekimin talebi kabul veya gerekçeli olarak reddetmesi.

Talep beklerken sorumlu hekim değişmez. Kabul işlemi sorumlu hekimi atomik biçimde
değiştirir; ret vakanın sorumlusunu etkilemez. Tamamlanmış, iptal edilmiş veya kesin
reddedilmiş vaka devredilemez. Karar verilmiş devir satırları güncellenemez ve hiçbir
devir kaydı silinemez. Her adım audit kaydı, uygulama içi bildirim ve e-posta üretir.

## Operasyon raporları

`GET /api/reports/cases`; tarih ve klinik filtreleriyle toplam/aktif/tamamlanan vaka,
iade, yeniden üretim, geciken iş, ortalama tamamlanma süresi, durum dağılımı, hekim iş
yükü, klinik dağılımı ve aşama sürelerini döndürür. Sonuç her rol için mevcut vaka
görünürlüğüyle sınırlandırılır; klinik yöneticisi yalnızca yönettiği klinikleri görür.
Rapor hasta adı, hasta kodu veya serbest klinik notu içermez.

Frontend rapor ekranı `http://localhost:5173/raporlar` adresindedir. Filtreler anlık
uygulanır; **PDF olarak yazdır** düğmesi toplulaştırılmış görünümü A4 rapora dönüştürür.

STL yükleme endpoint'leri:

- `POST /api/cases/{case_id}/uploads`: yükleme oturumu oluşturur.
- `GET /api/cases/{case_id}/uploads/{upload_id}`: kaydedilmiş byte ofsetini döndürür.
- `PATCH /api/cases/{case_id}/uploads/{upload_id}`: `Upload-Offset` başlığıyla sıradaki
  parçayı yükler. Gövde `application/offset+octet-stream` veya
  `application/octet-stream` olmalıdır.
- `POST /api/cases/{case_id}/uploads/{upload_id}/complete`: boyut ve SHA-256 kontrolü
  sonrasında dosya sürümünü oluşturur ve mesh doğrulamasını kuyruğa alır.
- `GET /api/cases/{case_id}/files/{file_version_id}`: yetki kontrolünden sonra dosyayı
  hasta bilgisi içermeyen güvenli bir adla indirir.

Varsayılan toplam dosya sınırı 512 MB, parça sınırı 8 MB ve yarım yükleme ömrü 24
saattir. Bu değerler `UPLOAD_MAX_BYTES`, `UPLOAD_CHUNK_MAX_BYTES` ve
`UPLOAD_SESSION_HOURS` ortam değişkenleriyle değiştirilebilir. Yükleme tamamlanmadan
`case_file_versions` kaydı oluşmaz. Tarayıcı dosyanın tamamının SHA-256 özetini ayrı
bir Web Worker içinde hesaplar; devam eden oturum yalnızca boyut ve tam özet aynıysa
kullanılır. Tamamlanan dosya SHA-256 ile sunucuda yeniden doğrulanır, atomik
olarak kalıcı klasöre taşınır ve `pending` mesh durumuyla kaydedilir.

Mesh worker; STL'nin okunabilirliğini, boş veya sonlu olmayan geometriyi, açık
kenarları, kapalı hacmi, winding tutarlılığını, dejenere ve tekrarlanan yüzleri,
non-manifold kenarları ve PyMeshLab ile gerçek yüzey kesişimlerini denetler. Doğrulama
izole alt süreçte çalışır; 5,5 milyon üçgen ve 10 dakika sınırı worker'ın tek bir
dosya yüzünden kilitlenmesini önler. Binary olmayan STL dosyaları ayrıca
`MESH_VALIDATION_MAX_ASCII_BYTES` boyut sınırına tabidir.

Taslaklar eksik kaydedilebilir; ancak zorunlu alanları veya geçerli mesh sonucu olan
bir tarama sürümü bulunmayan vaka yönetici onayına gönderilemez. Düzeltme talebinden
sonra aynı STL yeniden gönderilemez; geçerli yeni bir sürüm gerekir. Teknisyen yalnızca
laboratuvar aşamasına ulaşmış vakaları görür; API yanıtında hasta adı, klinik serbest
notları, dinamik alanlar, kullanıcı kimlikleri ve özgün dosya adı yer almaz. STL'nin
binary veya ASCII başlığındaki serbest ad bilgisi de kalıcı saklama öncesinde temizlenir.

Vaka detay ekranındaki Three.js tabanlı 3D önizleme STL dosyasını oturum kontrollü
dosya endpoint'inden alır. Sunucu büyük binary STL dosyaları için en fazla 250 bin
üçgenlik önizleme kopyasını akış halinde üretir; tarayıcı bu nedenle yüzlerce MB'lık
orijinali indirmek zorunda kalmaz. Büyük ASCII STL önizlemesi kaynak tüketimini
sınırlamak için reddedilir ve binary STL dönüşümü istenir. Ayrıştırma Web Worker içinde yapılır;
görüntüleyicide döndürme, kaydırma, yakınlaştırma, görünümü sıfırlama, tel kafes modu,
sürüm seçimi ve mesh doğrulama özeti bulunur. Önizleme en fazla 250 bin üçgen çizer;
orijinal STL üretim ve indirme için tam çözünürlükte saklanır.

## Yedekleme ve geri yükleme

PostgreSQL, tamamlanmış vaka dosyaları ve Firebase Emulator export'unu aynı manifest
altında yedeklemek için proje kökünde:

```powershell
.\scripts\backup.ps1
```

Yedekler varsayılan olarak Git dışında kalan `backups` klasörüne yazılır. Her dosyanın
SHA-256 özeti manifestte tutulur. Bir yedeği veri değiştirmeden doğrulamak için:

```powershell
.\scripts\restore.ps1 -BackupPath .\backups\dentalapp-YYYYMMDD-HHMMSS
```

`backend/.env` ve hasta verisi anahtarları bu yedeğe bilerek eklenmez. Anahtarların
ayrı güvenli yedeği bulunmadan veritabanı yedeği tek başına geri yüklenemez.

Gerçek geri yükleme için `-Apply` eklenir ve ekranda `RESTORE` onayı verilir. Betik
geri yükleme öncesinde otomatik yeni yedek alır; mevcut dosyaları silmek yerine
`storage\restore-rollback-*` altında geri dönüş noktası olarak saklar.
Geri yükleme sırasında API, worker, beat ve Firebase Emulator kapalı olmalıdır.

Veritabanı kayıtları ile fiziksel dosyaların uyumunu silme yapmadan denetlemek için:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.cli.check_storage
```

Sahipsiz dosyalar `--quarantine-orphans` seçeneğiyle silinmeden karantina klasörüne
taşınabilir. Eksik tamamlanmış dosyalar bulunduğunda komut hata koduyla sonlanır.

## Migration

PostgreSQL bağlantı bilgileri `backend/.env` içinde ayarlandıktan sonra:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
alembic upgrade head
```
