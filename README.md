# Knowly

Enterprise AI knowledge and research assistant built with Next.js, FastAPI, PostgreSQL, Redis, and optional external AI/search providers.

## What it provides

- Tenant-isolated document workspaces
- JWT authentication and administrator role controls
- PDF, DOCX, CSV, and text upload
- Local text extraction plus Apache Tika fallback
- 512-token-class document chunking
- Tenant-filtered hybrid-style BM25 scoring and optional Cohere reranking
- Grounded answers with source citations
- Optional OpenAI generation
- Docker Compose deployment with PostgreSQL, Redis, Tika, Next.js, FastAPI, and Nginx
- Health endpoint, security headers, upload limits, CI, and automated API tests

## Architecture

```text
Browser
  |
  v
Nginx
  +--> Next.js web application
  +--> FastAPI API
        +--> PostgreSQL metadata and document chunks
        +--> Apache Tika / local extractors
        +--> Redis / background task infrastructure
        +--> Optional Cohere reranking
        +--> Optional OpenAI generation
```

## Run locally

Requirements:

- Docker Desktop
- Python 3.12+ and Node.js 22+ for local development

Create environment configuration:

```powershell
Copy-Item .env.example .env
```

Set a secret of at least 32 characters in `.env`:

```text
JWT_SECRET=replace-with-a-long-random-secret
```

Start the production-style stack:

```powershell
docker compose up --build
```

Open:

- Application: http://localhost
- API documentation: http://localhost:8000/docs
- Direct API health: http://localhost:8000/health

## Local development

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install ".[test]"
Copy-Item ..\.env.example ..\.env
uvicorn app.main:app --reload
```

The backend uses SQLite when `DATABASE_URL` is a SQLite URL. It uses PostgreSQL in Docker by default.

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

## API

| Method | Route | Description |
|---|---|---|
| `GET` | `/health` | Service health |
| `POST` | `/auth/register` | Create tenant and administrator |
| `POST` | `/auth/login` | Obtain JWT |
| `POST` | `/documents` | Upload and queue document processing |
| `GET` | `/documents` | List tenant documents |
| `GET` | `/documents/{id}` | Read tenant document |
| `DELETE` | `/documents/{id}` | Delete document as administrator |
| `POST` | `/chat/query` | Ask a grounded question |

Send authenticated requests using `Authorization: Bearer <token>`.

## Security

- JWTs are signed and contain tenant identity and role
- Database queries filter document access by tenant
- Document retrieval also filters by tenant
- Upload type and size are validated
- Passwords use PBKDF2-SHA256 with 600,000 iterations
- Administrator APIs require the administrator role
- Security headers are added to every response
- API documentation is disabled in production
- `JWT_SECRET` must contain at least 32 characters

## Testing

```powershell
cd backend
pytest
```

GitHub Actions runs backend tests and validates the Next.js production build.

## Production checklist

- Replace all default credentials and secrets
- Configure HTTPS and terminate TLS at a managed proxy or load balancer
- Use managed PostgreSQL, Redis, object storage, and secrets
- Configure production CORS origins explicitly
- Set `OPENAI_API_KEY` and `COHERE_API_KEY` for hosted generation and reranking
- Run workers from a durable queue for large documents
- Add rate limiting and centralized structured logging
- Add malware scanning and MIME/content inspection before indexing
- Back up PostgreSQL and uploaded files
- Add external monitoring and alerting
