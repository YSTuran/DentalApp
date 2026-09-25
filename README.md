# DentalApp

Diş klinikleri ile laboratuvar arasındaki vaka, tasarım, onay, üretim ve teslim süreçlerini yöneten demo uygulaması.

> DEMO — Gerçek hasta verisi girmeyiniz.

## Mevcut iskelet

- FastAPI uygulama fabrikası
- Ortam değişkeni tabanlı yapılandırma
- PostgreSQL için SQLAlchemy bağlantı katmanı
- Redis ve Celery bağlantı katmanı
- Alembic migration altyapısı
- Firebase Authentication ve yerel Authentication Emulator desteği
- Klinik kapsamlı rol/yetki kontrol katmanı
- PostgreSQL seviyesinde değiştirilemez audit kayıtları
- Sistem yöneticisi için klinik yönetimi ekranı
- Firebase ile PostgreSQL'i birlikte yöneten kullanıcı ve rol API'si
- Liveness ve readiness endpoint'leri
- Pytest başlangıç testleri

## Yerel kurulum (PowerShell)

```powershell
cd backend
& 'C:\Users\Yusuf\AppData\Local\Programs\Python\Python313\python.exe' -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

Uygulama: `http://127.0.0.1:8000`

API belgeleri: `http://127.0.0.1:8000/docs`

Sağlık kontrolleri:

- `GET /api/health/live`: API sürecinin çalıştığını gösterir.
- `GET /api/health`: PostgreSQL, Redis ve Firebase bağlantılarını kontrol eder.

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

Endpoint; `action`, `entity_type`, `entity_id`, `actor_user_id` ve `clinic_id`
filtreleri ile `limit`/`offset` sayfalamasını destekler.

Backend yetki katmanı global rol, herhangi bir rol, klinik erişimi ve klinik rolü
kontrollerini ayrı ayrı uygular. Sistem yöneticisi klinik rolü gerektiren işlemleri
yalnızca ilgili kontrol açıkça izin veriyorsa devralabilir.

## Klinik API

- `GET /api/clinics`: sistem yöneticisi tüm klinikleri, klinik yöneticisi yalnızca
  aktif rol ataması bulunan klinikleri görür.
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
değişikliği yapılabilir.

## Kullanıcı ve rol API'si

- `GET /api/users`: sistem yöneticisi tüm kullanıcıları görür. Klinik yöneticisi
  yalnızca sorumlu olduğu kliniklerdeki hekim ve yönetici hekimleri görür; diğer
  kliniklere ait rol atamaları yanıtta gösterilmez.
- `GET /api/users/{user_id}`: aynı görünürlük kurallarıyla kullanıcı detayı.
- `POST /api/users`: Firebase hesabını, PostgreSQL kullanıcısını ve ilk rolü oluşturur.
- `PATCH /api/users/{user_id}`: ad-soyad bilgisini Firebase ve PostgreSQL'de günceller.
- `POST /api/users/{user_id}/deactivate` ve `reactivate`: hesabı iki sistemde birlikte
  pasifleştirir veya etkinleştirir; gerekçe zorunludur.
- `POST /api/users/{user_id}/roles`: yeni rol atar.
- `POST /api/users/{user_id}/roles/{assignment_id}/deactivate` ve `reactivate`:
  rol atamasının durumunu değiştirir; gerekçe zorunludur.

Kullanıcı silme endpoint'i yoktur. Kullanıcı oluşturmada üretilen geçici parola
yalnızca başarılı `POST /api/users` yanıtında bir kez döner ve audit kaydına yazılmaz.
Firebase işlemi sonrasında PostgreSQL/audit işlemi başarısız olursa yapılan Firebase
değişikliği telafi edilir. Son aktif sistem yöneticisi veya oturumdaki yöneticinin
kendi hesabı pasifleştirilemez.

## Frontend

Firebase Emulator, FastAPI ve React geliştirme sunucusunu birlikte başlatmak için
proje kökünde:

```powershell
npm run dev
```

Loglar aynı terminalde `FIREBASE`, `API` ve `WEB` etiketleriyle gösterilir. `Ctrl+C`
üç servisi de kapatır; Firebase kullanıcıları temiz kapanışta `firebase-export` klasörüne
kaydedilir. PostgreSQL servisinin ve Redis konteynerinin önceden çalışıyor olması gerekir.

Yalnızca React, TypeScript ve Vite tabanlı frontend'i çalıştırmak için:

```powershell
cd frontend
npm install
npm run dev
```

Uygulamayı `http://localhost:5173` adresinden açın. Geliştirme ortamı ayarları
`frontend/.env.local` dosyasından okunur; örnek değerler `frontend/.env.example`
içindedir. Firebase servis hesabı dosyası frontend'e eklenmez.

Giriş sırasında Firebase Auth Emulator'dan alınan ID token FastAPI'ye gönderilir.
FastAPI doğrulamadan sonra CSRF korumalı, HttpOnly bir oturum çerezi üretir.

## Test

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest
```

PostgreSQL trigger entegrasyon testlerini ayrıca çalıştırmak için:

```powershell
$env:RUN_DATABASE_INTEGRATION_TESTS='1'
pytest tests/integration/test_audit_immutability.py tests/integration/test_clinic_api.py tests/integration/test_user_management_api.py
```

## Migration

PostgreSQL bağlantı bilgileri `backend/.env` içinde ayarlandıktan sonra:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
alembic upgrade head
```
