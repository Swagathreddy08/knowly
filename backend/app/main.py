from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db, init_db
from .models import Document, DocumentChunk, DocumentStatus, Role, Tenant, User
from .processing import chunk_text, extract_text
from .retrieval import grounded_answer, retrieve_chunks
from .schemas import (
    AnswerResponse,
    Citation,
    DocumentResponse,
    LoginRequest,
    QuestionRequest,
    TenantRegistration,
    TokenResponse,
)
from .security import create_access_token, get_current_user, hash_password, require_admin, verify_password


@asynccontextmanager
async def lifespan(application: FastAPI):
    del application  # Database setup is intentionally driven by application startup.
    init_db()
    yield


app = FastAPI(
    title="Knowly API",
    version="1.0.0",
    docs_url="/docs" if settings.app_env != "production" else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if settings.app_env == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    del request
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "knowly-api"}


@app.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: TenantRegistration, db: Session = Depends(get_db)):
    existing = db.scalar(select(User).where(User.email == str(payload.email)))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")

    tenant = Tenant(name=payload.tenant_name)
    db.add(tenant)
    db.flush()
    user = User(
        tenant_id=tenant.id,
        email=str(payload.email).lower(),
        password_hash=hash_password(payload.password),
        role=Role.admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(
        access_token=create_access_token(user),
        tenant_id=tenant.id,
        role=user.role,
    )


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(
        select(User).where(
            User.tenant_id == payload.tenant_id,
            User.email == str(payload.email).lower(),
        )
    )
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(
        access_token=create_access_token(user),
        tenant_id=user.tenant_id,
        role=user.role,
    )


def process_document(document_id: str) -> None:
    db = next(get_db())
    try:
        document = db.get(Document, document_id)
        if not document:
            return

        document.status = DocumentStatus.processing
        document.error = None
        db.commit()

        extracted = extract_text(
            Path(document.storage_path),
            document.content_type,
            document.filename,
        )
        chunks = chunk_text(extracted)
        if not chunks:
            raise ValueError("No readable text was found in this document")

        db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document.id,
            DocumentChunk.tenant_id == document.tenant_id,
        ).delete(synchronize_session=False)
        for index, content in enumerate(chunks):
            db.add(
                DocumentChunk(
                    tenant_id=document.tenant_id,
                    document_id=document.id,
                    chunk_index=index,
                    content=content,
                )
            )
        document.chunk_count = len(chunks)
        document.status = DocumentStatus.indexed
        db.commit()
    except Exception as exc:
        db.rollback()
        document = db.get(Document, document_id)
        if document:
            document.status = DocumentStatus.failed
            document.error = str(exc)[:2000]
            db.commit()
    finally:
        db.close()


@app.post("/documents", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    allowed = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/csv",
        "text/plain",
    }
    content_type = file.content_type or "application/octet-stream"
    if content_type not in allowed:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported file type")

    data = await file.read(settings.max_upload_size_mb * 1024 * 1024 + 1)
    if len(data) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File is too large")

    tenant_dir = settings.upload_dir / user.tenant_id
    tenant_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "upload").name
    unique_name = f"{uuid4().hex}-{safe_name}"
    storage_path = tenant_dir / unique_name
    storage_path.write_bytes(data)

    document = Document(
        tenant_id=user.tenant_id,
        filename=safe_name,
        content_type=content_type,
        storage_path=str(storage_path),
        status=DocumentStatus.uploaded,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    background_tasks.add_task(process_document, document.id)
    return document


@app.get("/documents", response_model=list[DocumentResponse])
def list_documents(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(Document)
        .where(Document.tenant_id == user.tenant_id)
        .order_by(Document.created_at.desc())
    ).all()


@app.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = db.scalar(
        select(Document).where(Document.id == document_id, Document.tenant_id == user.tenant_id)
    )
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


@app.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    document = db.scalar(
        select(Document).where(Document.id == document_id, Document.tenant_id == user.tenant_id)
    )
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    try:
        Path(document.storage_path).unlink(missing_ok=True)
    except OSError:
        pass
    db.delete(document)
    db.commit()


@app.post("/chat/query", response_model=AnswerResponse)
def query_knowledge(
    payload: QuestionRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    indexed_document_ids = db.scalars(
        select(Document.id).where(
            Document.tenant_id == user.tenant_id,
            Document.status == DocumentStatus.indexed,
        )
    ).all()
    if not indexed_document_ids:
        return AnswerResponse(answer="No processed documents are available.", citations=[])

    chunks = db.scalars(
        select(DocumentChunk)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(
            DocumentChunk.tenant_id == user.tenant_id,
            DocumentChunk.document_id.in_(indexed_document_ids),
        )
    ).all()
    results = retrieve_chunks(list(chunks), payload.question, payload.top_k)
    answer = grounded_answer(payload.question, results)
    citations = [
        Citation(
            document_id=chunk.document_id,
            filename=chunk.document.filename,
            chunk_index=chunk.chunk_index,
            excerpt=chunk.content[:500],
        )
        for chunk, _ in results
    ]
    return AnswerResponse(answer=answer, citations=citations)
