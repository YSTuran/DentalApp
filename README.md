# DentalApp

Diş klinikleri ile laboratuvar arasındaki vaka, tasarım, onay, üretim ve teslim süreçlerini yöneten demo uygulaması.

> DEMO — Gerçek hasta verisi girmeyiniz.

## Mevcut iskelet

- FastAPI uygulama fabrikası
- Ortam değişkeni tabanlı yapılandırma
- PostgreSQL için SQLAlchemy bağlantı katmanı
- Redis ve Celery bağlantı katmanı
- Alembic migration altyapısı
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
- `GET /api/health`: PostgreSQL ve Redis bağlantılarını da kontrol eder.

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

