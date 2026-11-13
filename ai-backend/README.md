# OrbisERP AI Layer — Backend Foundation

Dedicated backend foundation for the **OrbisERP AI Layer** (Orbis Car Manufacturing Pvt. Ltd.).

This service acts as an asynchronous AI processing layer that communicates with **Groq LLM** on the backend and bridges with **ERPNext v16** via secured REST APIs without disturbing or modifying core ERPNext workflows.

---

## 1. Architecture Overview

```text
[Frappe Desk SPA (http://localhost:8085)]
               │
               ▼ (Browser Fetch / CORS)
[Orbis AI Backend (FastAPI :8000)]
       │                      │
       ▼ (Server-Side HTTPS)  ▼ (Server-Side REST / Token Auth)
  [Groq Cloud API]       [ERPNext Backend (:8085)]
```

### Why a Standalone FastAPI Microservice?
1. **Asynchronous Concurrency**: AI workloads (LLM generation, token streaming, tool executions) are I/O bound. FastAPI (async ASGI) handles streaming without blocking ERPNext's synchronous Gunicorn WSGI workers.
2. **Zero Core Risk**: If the AI service restarts, scales, or hits external API limits, ERPNext core manufacturing, stock, and finance operations remain completely unaffected.
3. **Dependency Isolation**: AI dependencies (`pydantic`, `groq`, `httpx`) are isolated in their own virtual environment, preserving Frappe's Python 3.14 environment integrity.

---

## 2. Directory Structure

```text
ai-backend/
├── .env.example          # Environment variable template (placeholders only)
├── .gitignore            # Git exclusion rules for virtualenvs and secrets
├── requirements.txt      # Initial foundation dependencies
├── README.md             # This setup and architecture documentation
└── app/
    ├── __init__.py
    ├── main.py           # FastAPI entry point & CORS configuration
    ├── core/
    │   ├── __init__.py
    │   └── config.py     # Pydantic Settings & environment validation
    └── api/
        ├── __init__.py
        └── routes/
            ├── __init__.py
            └── health.py # Health & status monitoring endpoint
```

---

## 3. Setup Instructions (When Approved)

> [!NOTE]
> Dependencies have **not** been installed and the service has **not** been started, adhering to strict review protocols.
> Once approved, execute the following steps in your terminal:

### Step 1: Create a Dedicated Python Virtual Environment
```powershell
cd E:\Orbis-ERP\ai-backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Step 2: Install Foundation Dependencies
```powershell
pip install -r requirements.txt
```

### Step 3: Configure Environment
Copy `.env.example` to `.env` and fill in your placeholders:
```powershell
copy .env.example .env
```

### Step 4: Run the Development Server
```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 4. Endpoints Available in Foundation

* **`GET /`**: Service verification index.
* **`GET /api/health`**: Health status, target module verification (`Stock`), and operational readiness.

---

## 5. Security & Isolation Controls

* **Zero Secret Exposure**: No API keys, passwords, or salts exist in repository files or client-facing responses.
* **Database Isolation**: The AI layer does **not** connect directly to MariaDB. It uses authenticated server-to-server REST interfaces.
* **Single User & Stock Scope**: Configuration explicitly isolates the test environment to the designated user email and the `Stock` module.

