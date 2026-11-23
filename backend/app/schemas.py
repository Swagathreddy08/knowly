from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import DocumentStatus, Role


class TenantCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=1024)
    role: Role = Role.member


class TenantRegistration(BaseModel):
    tenant_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(min_length=12, max_length=1024)


class LoginRequest(BaseModel):
    tenant_id: str
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant_id: str
    role: Role


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    content_type: str
    status: DocumentStatus
    chunk_count: int
    error: str | None
    created_at: datetime


class QuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=4000)
    top_k: int = Field(default=5, ge=1, le=20)


class Citation(BaseModel):
    document_id: str
    filename: str
    chunk_index: int
    excerpt: str


class AnswerResponse(BaseModel):
    answer: str
    citations: list[Citation]
