# 📄 Docxy

**High‑Performance PDF Table Extraction API**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![MIT License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](https://github.com/yourusername/docxy/pulls)

---

## ✨ Features

- **🔑 API Key Authentication** – Secure access for every endpoint (except health checks).
- **⚡ Asynchronous Processing** – Long‑running PDF jobs are handled in the background via Celery (or fallback to FastAPI `BackgroundTasks`).
- **📊 Smart Table Extraction** – Uses **Camelot** (lattice/stream) as primary engine, falls back to **pdfplumber** for borderless tables.
- **📝 Markdown‑Ready Text** – Extracted document text includes placeholders like `[Table 1]` that match the sheet names in the generated Excel file.
- **🧩 Hybrid Architecture** – Combines multiple extraction libraries for maximum coverage.
- **🐳 Docker Ready** – Full `docker-compose` setup for development and production.
- **📈 Scalable** – Redis/Celery support for distributed job processing.
- **🛠️ Easy Configuration** – All settings via environment variables (`.env`).

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- [Ghostscript](https://ghostscript.com/releases/gsdnld.html) (required by Camelot on Windows)
- (Optional) Redis – for Celery broker and rate limiting

### Installation

```bash
# Clone the repository
git clone https://github.com/arnalph/docxy.git
cd docxy

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate      # Linux/macOS
venv\Scripts\activate          # Windows

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Copy the example environment file and adjust as needed:

```bash
cp .env.example .env
```

For a local, zero‑dependency run, use:

```ini
DATABASE_URL=sqlite+aiosqlite:///./docxy.db
USE_REDIS=False
STORAGE_TYPE=local
UPLOAD_DIR=uploads
```

### Database Setup

```bash
alembic upgrade head
```

### Create an Admin User & API Key

```bash
python app/core/init_admin.py
```

This will output an API key like `sk_...`. Save it – you’ll need it for authentication.

### Run the Server

```bash
python run.py
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### (Optional) Start a Celery Worker

If you have Redis enabled, start a worker in another terminal:

```bash
celery -A app.core.celery_app worker --loglevel=info
```

---

## 📚 API Documentation

All endpoints (except `/health`) require an API key sent in the `Authorization` header:

```
Authorization: Bearer <your-api-key>
```

### `POST /api/v1/jobs`

Upload a PDF for processing.

- **Request**: `multipart/form-data` with a `file` field (PDF only).
- **Response**: `201 Created` with job ID and initial status.

```bash
curl -X POST "http://localhost:8000/api/v1/jobs" \
  -H "Authorization: Bearer sk_..." \
  -F "file=@document.pdf"
```

### `GET /api/v1/jobs/{job_id}`

Poll job status.

- **Response**: JSON with `status` (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`), progress, and error message.

### `GET /api/v1/jobs/{job_id}/download`

Retrieve the extracted data once the job is `COMPLETED`.

- **Response**: JSON containing:
  - `download_url`: URL to download the Excel file.
  - `full_text`: Markdown text of the PDF with `[Table N]` placeholders.

### `GET /api/v1/health`

Public endpoint that returns the health status of the API and its dependencies.

### `GET /api/v1/admin`

A simple admin dashboard (no authentication – use only in development).

---

## 🔧 Configuration

Key environment variables (see `.env.example` for all):

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `sqlite+aiosqlite:///./docxy.db` |
| `USE_REDIS` | Enable Redis for Celery & rate limiting | `False` |
| `REDIS_URL` | Redis connection URL | – |
| `STORAGE_TYPE` | `local` or `s3` | `local` |
| `UPLOAD_DIR` | Local upload directory | `uploads` |
| `POPPLER_PATH` | Path to poppler binaries (Windows only) | – |
| `CAMELOT_FLAVOR` | Default Camelot flavor | `lattice` |
| `USE_PDFPLUMBER_FALLBACK` | Fallback to pdfplumber if Camelot finds no tables | `True` |
| `DEBUG` | Enable debug logging | `False` |

---

## 🏗️ Architecture

Docxy is built with a modular, async‑first design:

- **FastAPI** handles HTTP requests, authentication, and job dispatching.
- **SQLAlchemy** (async) with **Alembic** for database migrations.
- **Celery** (optional) processes PDF jobs in the background; falls back to FastAPI `BackgroundTasks` when Redis is unavailable.
- **Camelot** + **pdfplumber** extract tables and full text.
- **Storage Service** abstracts between local filesystem and S3/MinIO.

```
┌────────────┐    ┌────────────┐    ┌────────────┐
│  Client    │───▶│   FastAPI  │───▶│   Celery   │
└────────────┘    └────────────┘    └────────────┘
                          │                │
                          ▼                ▼
                   ┌────────────┐    ┌────────────┐
                   │   DB/Redis │    │ Extraction │
                   │            │    │  Service   │
                   └────────────┘    └────────────┘
```

---

## 🤝 Contributing

Contributions are welcome! Please open an issue or submit a pull request. For major changes, please discuss first.

---

<div align="center">Made with ❤️ and ☕</div>
```
