# DentFlow

DentFlow; diş klinikleri ile laboratuvar arasındaki dijital vaka, STL tarama,
tasarım onayı, üretim, teslim ve iade süreçlerini tek bir iş akışında yöneten web
uygulamasıdır. Proje yerel geliştirme ve eğitim amacıyla hazırlanmıştır.

> **DEMO — Gerçek hasta verisi girmeyiniz.**
>
> Uygulamada yalnızca tamamen uydurma hasta, kullanıcı ve klinik bilgileri
> kullanılmalıdır. Mevcut güvenlik önlemleri, uygulamanın üretim ortamına hazır
> olduğu anlamına gelmez.

## Temel özellikler

- Klinik kapsamlı rol ve yetki yönetimi
- Dinamik alanlara ve zorunlu alan doğrulamasına sahip vaka formu
- Büyük STL dosyaları için parçalı ve devam ettirilebilir yükleme
- Celery üzerinden asenkron STL mesh doğrulaması
- Tarayıcı içinde STL önizleme
- Silinmeyen ve kilitlenebilen dosya sürümleri
- Atlanamayan yönetici ve sorumlu hekim onayları
- Tasarım, üretim, malzeme/lot, kargo, teslim ve iade takibi
- Hedef hekimin kabulüyle tamamlanan vaka devri
- Bağlantılı yeni vaka oluşturan yeniden üretim süreci
- Uygulama içi bildirimler, e-posta kuyruğu ve bekleme süresi uyarıları
- Hasta kimliği içermeyen operasyon raporları ve PDF çıktıları
- Barkodlu teknisyen iş emri
- Değiştirilemeyen audit kayıtları
- Kullanıcıya özel açık/koyu görünüm ve renk paletleri
- Hasta alanları için uygulama katmanında şifreleme
- PostgreSQL, vaka dosyaları ve Firebase Emulator verileri için yedekleme

## Vaka akışı

Ana süreç aşağıdaki sırayı izler:

```text
Taslak
  → Yönetici hekim incelemesi
  → Laboratuvar tasarımı
  → Sorumlu hekim tasarım onayı
  → Üretim
  → Kargo
  → Şubeye teslim
```

Yönetici hekim tarama için düzeltme isteyebilir veya vakayı kesin olarak
reddedebilir. Sorumlu hekim laboratuvar tasarımına düzeltme isteyebilir. Teslim
edilen ürün iade edilirse teknisyen iadeyi kaydeder; yönetici hekim yeniden üretim
ya da yeni tarama kararı verir.

İki onay atlanamaz. Onaylanan dosya sürümü kilitlenir ve onay geri alınamaz.
Düzeltmeler yeni bir sürüm üzerinden yapılır. Kayıtlar silinmez; yanlış açılan vaka
gerekçesiyle iptal edilir.

Ayrıntılı durum ve geçiş kuralları [vaka iş akışı belgesinde](docs/case-workflow.md)
yer alır.

## Roller ve yetkiler

| Rol | Temel yetkiler |
| --- | --- |
| Sistem yöneticisi | Klinik ve kullanıcı yönetimi, tüm klinikleri görüntüleme, audit kayıtları ve raporlar |
| Klinik yöneticisi | Yetkili kliniklerde personel görünümü, vaka takibi, vaka devri, teslim doğrulama ve raporlar |
| Yönetici hekim | Klinik vakalarını inceleme, onaylama, düzeltme/ret kararı, iade kararı ve raporlar |
| Hekim | Vaka oluşturma, STL yükleme, gönderme ve sorumlusu olduğu tasarımı onaylama |
| Klinik personeli | Hekim adına vaka oluşturma, tarama yükleme, gönderme ve teslim doğrulama |
| Laboratuvar teknisyeni | Tasarım yükleme, üretim, malzeme/lot, kargo ve iade kaydı |

Rol ile klinik ataması ayrı tutulur. Bir kullanıcının tek bir aktif rolü, fakat rolü
uygunsa birden fazla aktif klinik ataması olabilir. Her vaka; işlemin yapıldığı
kliniği, vakayı açan kullanıcıyı ve güncel sorumlu hekimi ayrı ayrı saklar.

Vaka devri kabul edildiğinde önceki hekim geçmişte “vakayı açan kullanıcı” olarak
kalır ancak sıradan hekim yetkisiyle vakayı artık göremez ve operasyonel bildirim
almaz. Hedef hekim güncel sorumlu olur. Yönetici hekimler klinik kapsamındaki yönetim
yetkileri nedeniyle ilgili klinik vakalarını görmeye devam eder.

Laboratuvar teknisyeni hasta adını göremez. Sistem yöneticisi de global yönetim rolü
nedeniyle hasta adına otomatik erişim kazanmaz.

## Kullanılan teknolojiler

### Backend

- Python 3.13
- FastAPI
- SQLAlchemy 2
- Alembic
- PostgreSQL
- Redis
- Celery ve Celery Beat
- Firebase Admin SDK
- Trimesh ve PyMeshLab

### Frontend

- React
- TypeScript
- Vite
- Firebase Web SDK
- Three.js
- Vitest ve Testing Library

### Yerel yardımcı servisler

- Firebase Authentication Emulator
- Docker üzerinde Mailpit
- Docker veya yerel kurulum üzerinden Redis

## Proje yapısı

```text
DentFlow/
├── backend/
│   ├── app/                 FastAPI, servisler, modeller ve CLI araçları
│   ├── migrations/          Alembic veritabanı migration dosyaları
│   └── tests/               Backend birim ve entegrasyon testleri
├── frontend/
│   └── src/                 React uygulaması ve frontend testleri
├── docs/
│   └── case-workflow.md     Vaka durumları ve iş kuralları
├── scripts/                 Yedekleme, geri yükleme ve geliştirme araçları
├── storage/                 Yerel dosyalar ve çalışma verileri; Git'e eklenmez
├── docker-compose.yml       Yerel Mailpit servisi
├── firebase.json            Firebase Emulator yapılandırması
└── package.json             Birleşik geliştirme ve doğrulama komutları
```

## Gereksinimler

Yerel Windows geliştirme ortamında aşağıdaki araçlar gereklidir:

- Python 3.13
- Node.js 24 veya uyumlu güncel LTS sürümü
- npm
- PostgreSQL
- Docker Desktop
- Firebase Emulator için Java çalışma ortamı
- Git

Komutlar PowerShell için verilmiştir. PostgreSQL ve Docker Desktop çalışır durumda
olmalıdır.

## İlk kurulum

### 1. Node.js bağımlılıkları

Proje kökünde:

```powershell
npm ci
npm --prefix frontend ci
```

### 2. Python sanal ortamı

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.lock
python -m pip install -e . --no-deps
cd ..
```

`backend/requirements.lock` Windows geliştirme ortamı içindir. CI ortamı Linux için
`backend/requirements-linux.lock` dosyasını kullanır.

### 3. PostgreSQL veritabanı

PostgreSQL üzerinde uygulamaya özel bir kullanıcı ve veritabanı oluşturun. Aşağıdaki
değerler yalnızca örnektir; parolayı kendiniz belirleyin:

```sql
CREATE USER dentalapp_user WITH PASSWORD 'CHANGE_ME';
CREATE DATABASE dentalapp OWNER dentalapp_user;
```

Gerçek parola README, kaynak kod veya Git geçmişine yazılmamalıdır.

### 4. Redis

Redis'i Docker ile ilk kez oluşturmak için:

```powershell
docker run --name dentalapp-redis -p 127.0.0.1:6379:6379 -d redis:7-alpine
```

Daha sonraki çalıştırmalarda mevcut konteyneri başlatmak yeterlidir:

```powershell
docker start dentalapp-redis
```

### 5. Ortam değişkenleri

Backend için `backend/.env`, frontend için `frontend/.env` dosyası kullanılır. Bu
dosyalar Git tarafından izlenmez. Gerçek anahtarları veya parolaları README'ye,
ekran görüntülerine ya da commit geçmişine eklemeyin.

Örnek backend yapılandırması:

```dotenv
APP_NAME=DentFlow API
APP_ENV=development
APP_DEBUG=true
DEMO_MODE=true
API_PREFIX=/api

DATABASE_URL=postgresql+psycopg://dentalapp_user:CHANGE_ME@localhost:5432/dentalapp
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=GENERATE_A_RANDOM_SECRET
CORS_ORIGINS=["http://localhost:5173"]
STORAGE_PATH=../storage

FIREBASE_PROJECT_ID=USE_THE_CONFIGURED_PROJECT_ID
FIREBASE_USE_EMULATOR=true
FIREBASE_AUTH_EMULATOR_HOST=127.0.0.1:9099
COOKIE_SECURE=false

PATIENT_DATA_KEYS={"v1":"BASE64_ENCODED_32_BYTE_KEY"}
PATIENT_DATA_ACTIVE_KEY_ID=v1
PATIENT_LOOKUP_KEY=DIFFERENT_BASE64_ENCODED_32_BYTE_KEY
```

Örnek frontend yapılandırması:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
VITE_FIREBASE_PROJECT_ID=USE_THE_SAME_PROJECT_ID
VITE_FIREBASE_API_KEY=demo-api-key
VITE_FIREBASE_AUTH_DOMAIN=USE_THE_SAME_PROJECT_ID.firebaseapp.com
VITE_FIREBASE_APP_ID=demo-app-id
VITE_FIREBASE_USE_EMULATOR=true
VITE_FIREBASE_AUTH_EMULATOR_URL=http://127.0.0.1:9099
```

`FIREBASE_PROJECT_ID` ve `VITE_FIREBASE_PROJECT_ID`, projenin Firebase Emulator
yapılandırmasındaki proje kimliğiyle aynı olmalıdır.

> **Uyumluluk notu:** Uygulamanın görünen ürün adı **DentFlow**'dur. Mevcut yerel
> kurulumları ve kayıtları bozmamak için `dentalapp` veritabanı/kullanıcı adı,
> Redis konteyner adı ve Firebase proje kimliği örneklerde korunmuştur. Bunlar ürün
> adı değil, çalışan ortama bağlı teknik kimliklerdir; ancak planlı bir veri ve
> altyapı geçişiyle değiştirilebilir.

Güvenli rastgele değer üretmek için aşağıdaki komutlar kullanılabilir:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
python -c "import base64,secrets; print(base64.b64encode(secrets.token_bytes(32)).decode())"
```

İkinci komutu hasta verisi şifreleme anahtarı ve arama anahtarı için ayrı ayrı
çalıştırın; iki ayarda aynı değeri kullanmayın.

### 6. Veritabanı migration'ları

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
alembic upgrade head
cd ..
```

### 7. Uygulamayı başlatma

Proje kökünde:

```powershell
npm run dev
```

Bu komut aşağıdaki süreçleri tek terminalde başlatır:

- Firebase Authentication Emulator
- Mailpit test e-posta sunucusu
- FastAPI
- Genel Celery worker
- STL mesh worker
- Celery Beat
- React/Vite geliştirme sunucusu

Loglar `FIREBASE`, `MAIL`, `API`, `WORKER`, `MESH`, `BEAT` ve `WEB` etiketleriyle
gösterilir. Celery ayrıca açılmaz; worker ve beat süreçleri bu komutun içindedir.

### 8. İlk sistem yöneticisi

Firebase Emulator çalışırken ikinci bir terminal açın:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m app.cli.create_admin
```

Komut e-posta, ad-soyad ve parola bilgilerini etkileşimli olarak ister. Parola
terminalde açık biçimde gösterilmez.

## Günlük çalıştırma

1. PostgreSQL ve Docker Desktop'ı başlatın.
2. Redis konteynerini başlatın: `docker start dentalapp-redis`
3. Proje kökünde `npm run dev` çalıştırın.
4. Uygulamayı `http://localhost:5173` adresinden açın.
5. İşiniz bittiğinde terminalde `Ctrl+C` kullanın.

Firebase Emulator kullanıcıları temiz kapanışta `firebase-export` klasörüne
kaydedilir. Süreç zorla kapatılırsa son kullanıcı değişiklikleri export dosyasına
yazılamayabilir.

## Yerel adresler

| Servis | Adres |
| --- | --- |
| Web uygulaması | `http://localhost:5173` |
| FastAPI | `http://127.0.0.1:8000` |
| Swagger/OpenAPI | `http://127.0.0.1:8000/docs` |
| Firebase Emulator UI | `http://127.0.0.1:4000` |
| Firebase Auth Emulator | `http://127.0.0.1:9099` |
| Mailpit gelen kutusu | `http://localhost:8025` |
| Redis | `127.0.0.1:6379` |

Sağlık endpoint'leri:

- `GET /api/health/live`: API sürecinin çalıştığını doğrular.
- `GET /api/health`: PostgreSQL, Redis, Firebase ve arka plan süreçlerini denetler.

Servisler ilk açıldığında worker ve beat kalp atışlarının görünmesi birkaç saniye
sürebilir.

## Kullanıcı ve Firebase yönetimi

Yeni personel hesabı sistem yöneticisi tarafından uygulama içinden oluşturulur.
Firebase için üretilen geçici parola yalnızca bir kez gösterilir ve audit kaydına
yazılmaz.

PostgreSQL kaydı bulunduğu halde kullanıcı Firebase Emulator içinde yoksa, emulator
çalışırken proje kökünde şu komutu kullanın:

```powershell
npm run firebase:user:repair -- --email <kullanici-e-postasi>
```

Hesap mevcutsa ancak yerel parolası yenilenecekse:

```powershell
npm run firebase:user:repair -- --email <kullanici-e-postasi> --reset-password
```

Bu araç yalnızca Firebase Emulator için çalışır. Gerçek Firebase hesabında otomatik
onarım yapmaz.

## Dosya yükleme ve STL doğrulama

STL yüklemeleri parçalara ayrılır, kesinti sonrasında devam ettirilebilir ve SHA-256
özetiyle doğrulanır. Varsayılan dosya sınırı 300 MB'dır. Kullanıcı başına eşzamanlı
yükleme sayısı ve ayrılmış toplam boyut ayrıca sınırlandırılır.

Mesh worker aşağıdaki kontrolleri gerçekleştirir:

- Dosyanın okunabilir ve geçerli geometri içermesi
- Açık kenar ve kapalı hacim durumu
- Non-manifold kenarlar
- Dejenere veya tekrarlanan yüzler
- Winding tutarlılığı
- Gerçek yüzey kesişimleri

Geçerli tarama olmadan vaka yönetici incelemesine gönderilemez. Onaylanan dosya
değiştirilemez; düzeltme için yeni bir sürüm yüklenir. Tarayıcı önizlemesi büyük
dosyalarda sınırlı üçgen sayısına sahip bir önizleme üretir, üretim dosyasını
değiştirmez.

## Bildirim ve e-posta

Vaka durum değişiklikleri ilgili kullanıcıya uygulama içi bildirim oluşturur. Aynı
işlem, SMTP üzerinden gönderilmek üzere e-posta kuyruğuna eklenir. Gönderim API
isteğini bekletmez ve geçici hatalarda tekrar denenir.

Yerel ortamda e-postalar gerçek alıcılara gönderilmez. Mailpit bütün test
mesajlarını `http://localhost:8025` adresinde gösterir. `.test` veya `.invalid`
uzantılı uydurma adresler kullanılabilir.

Bildirim ve e-posta içeriklerinde hasta adı bulunmaz. Vaka devrinden sonra
operasyonel hekim bildirimleri güncel sorumlu hekime gider.

Bekleme süresi eşikleri `CASE_WAIT_WARNING_HOURS` ortam değişkeniyle JSON olarak
özelleştirilebilir. Aynı vaka aşaması için aynı kullanıcıya tekrar uyarı üretilmez.

## Güvenlik ve veri koruma

- Oturum açma Firebase Authentication üzerinden yapılır.
- FastAPI, doğrulanmış Firebase token'ından sonra HttpOnly oturum çerezi üretir.
- Yazma işlemleri CSRF koruması kullanır.
- API yanıtları varsayılan olarak `Cache-Control: no-store` içerir.
- Hasta adı, hasta kodu, klinik notları ve diğer hassas alanlar AES-256-GCM ile
  şifrelenir.
- Hasta kodu araması ayrı anahtarla oluşturulan HMAC kör indeksi üzerinden tam
  eşleşme yapar.
- Audit kayıtlarına hasta alanlarının açık değerleri yazılmaz.
- Audit, onay ve durum geçmişi kayıtları veritabanı seviyesinde silme/değiştirmeye
  karşı korunur.
- Kilitlenen STL ve tasarım sürümleri değiştirilemez.

`backend/.env`, `frontend/.env`, `firebase-export`, `storage`, `backups` ve Firebase
servis hesabı dosyaları Git'e eklenmez. Şifreleme anahtarları kaybolursa şifreli hasta
alanları geri getirilemez; anahtarlar veritabanı yedeğinden ayrı ve güvenli bir yerde
saklanmalıdır.

## Raporlar ve çıktılar

Operasyon raporları yalnızca sistem yöneticisi, klinik yöneticisi ve yönetici hekim
tarafından görüntülenebilir. Raporlar kullanıcının klinik kapsamını uygular ve hasta
kimliği içermez.

Filtrelenmiş audit kayıtları kategori renklerini koruyan kutulu PDF çıktısı olarak
yazdırılabilir. Bütün roller vaka iş emri oluşturabilir; yalnızca teknisyen çıktısında
vaka numarasını taşıyan Code 128 barkod bulunur.

## Yedekleme ve geri yükleme

Yedek aşağıdaki bileşenleri birlikte saklar:

- PostgreSQL veritabanı
- Tamamlanmış vaka dosyaları
- Firebase Emulator export'u
- Dosya boyutu ve SHA-256 özetlerini içeren manifest
- Şifreleme anahtarlarının kendisi yerine karşılaştırma parmak izleri

Yedek oluşturmak için:

```powershell
npm run backup
```

Yedekler Git dışında kalan `backups` klasörüne yazılır.

Bir yedeği veri değiştirmeden doğrulamak için:

```powershell
.\scripts\restore.ps1 -BackupPath .\backups\dentflow-YYYYMMDD-HHMMSS
```

Geri yüklemeyi uygulamak için API, worker, beat ve Firebase Emulator süreçlerini
kapatın, ardından:

```powershell
.\scripts\restore.ps1 -BackupPath .\backups\dentflow-YYYYMMDD-HHMMSS -Apply
```

Betik kullanıcıdan `RESTORE` onayı ister, mevcut durum için otomatik güvenlik yedeği
oluşturur ve önceki dosyaları `storage/restore-rollback-*` altında saklar. Boş ve henüz
DentFlow tabloları oluşturulmamış hedef veritabanına geri yükleme desteklenir.

Veritabanı ile fiziksel dosyaların uyumunu değiştirme yapmadan denetlemek için:

```powershell
npm run storage:check
```

Eksik dosya varsa normal yedekleme durdurulur. Sahipsiz dosyalar istenirse
`backend` klasöründe `python -m app.cli.check_storage --quarantine-orphans`
komutuyla silinmeden karantinaya taşınabilir.

## Test ve kod kalitesi

| Komut | Açıklama |
| --- | --- |
| `npm run test:quick` | Veritabanı gerektirmeyen backend testleri ve frontend testleri |
| `npm test` | Backend birim/entegrasyon ve frontend testleri |
| `npm run lint` | Ruff ve ESLint kontrolleri |
| `npm run build` | TypeScript ve Vite üretim derlemesi |
| `npm run verify` | Test, lint ve build kontrollerinin tamamı |
| `npm run verify:full` | Doğrulamalara Firebase Emulator testini de ekler |
| `npm run security:audit` | Python ve npm bağımlılık güvenlik taraması |

`npm run verify:full` Firebase Emulator'ı geçici olarak başlatacağı için geliştirme
servisleri kapalıyken çalıştırılmalıdır. Entegrasyon testleri migration uygulanmış
PostgreSQL şeması gerektirir; test işlemleri dış transaction sonunda geri alınır.

GitHub Actions aynı temel test, lint, derleme ve güvenlik kontrollerini Linux üzerinde
çalıştırır.

## Sık karşılaşılan sorunlar

### Firebase Emulator portu kullanımda

Önceki emulator süreci tam kapanmamış olabilir. `4000`, `4400`, `4500` ve `9099`
portlarını kullanan süreçleri kontrol edin. Aynı anda yalnızca bir Firebase Emulator
çalıştırın.

### Girişte 401 hatası

Kullanıcının PostgreSQL kaydı bulunmasına rağmen Firebase Emulator hesabı eksik
olabilir. Emulator UI üzerinden hesabı kontrol edin ve gerekirse
`firebase:user:repair` komutunu kullanın.

### FastAPI başlatılırken WinError 10013

`8000` portu başka bir süreç tarafından kullanılıyor veya güvenlik yazılımı bağlantıyı
engelliyor olabilir. Portu kullanan eski Uvicorn sürecini kapatın ve uygulamayı yeniden
başlatın.

### Celery ekranı bulunamıyor

Celery'nin ayrı bir arayüzü yoktur. `npm run dev` terminalindeki `WORKER`, `MESH` ve
`BEAT` etiketli satırlar arka plan süreçlerinin loglarıdır.

### STL doğrulaması başarısız

Worker logundaki hata yerine vaka detayındaki mesh raporunu inceleyin. Dosyanın gerçek
bir STL olduğundan, boş olmadığından, sınırları aşmadığından ve mümkünse kapalı bir
mesh içerdiğinden emin olun.

## Üretim ortamı notu

Bu depo yerel demo ve eğitim ortamına yöneliktir. Gerçek kullanımdan önce en azından
aşağıdaki çalışmalar ayrıca yapılmalıdır:

- HTTPS ve güvenli çerez yapılandırması
- Gerçek Firebase projesi ve servis hesabı yönetimi
- Yönetilen PostgreSQL, Redis, dosya depolama ve SMTP hizmetleri
- Anahtar kasası ve düzenli anahtar rotasyonu
- Merkezi loglama, izleme ve alarm sistemi
- Otomatik, şifreli ve geri yükleme testi yapılmış yedekler
- KVKK kapsamı, saklama süreleri ve erişim politikaları için hukuki/güvenlik incelemesi
- Yük, güvenlik, felaket kurtarma ve kullanıcı kabul testleri

Bu kontroller tamamlanmadan sisteme gerçek hasta verisi girilmemelidir.
