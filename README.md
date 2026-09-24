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

## Migration

PostgreSQL bağlantı bilgileri `backend/.env` içinde ayarlandıktan sonra:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```
