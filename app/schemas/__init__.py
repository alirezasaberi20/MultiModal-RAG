from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ── Auth ──

class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: int | None = None


# ── Documents ──

class DocumentResponse(BaseModel):
    id: int
    original_name: str
    status: str
    chunk_count: int
    file_size_bytes: int = 0
    processing_time_ms: int | None = None
    created_at: datetime
    error_message: str | None = None

    model_config = {"from_attributes": True}


# ── Chat ──

class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    document_ids: list[int] | None = None
    conversation_id: int | None = None


class SourceChunk(BaseModel):
    content: str
    chunk_type: str
    page: int | None = None
    document_name: str | None = None
    score: float | None = None


class CostBreakdown(BaseModel):
    embedding_tokens: int = 0
    chat_input_tokens: int = 0
    chat_output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    latency_ms: int = 0


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    conversation_id: int | None = None
    cost: CostBreakdown | None = None


# ── Conversations ──

class ConversationCreate(BaseModel):
    title: str = Field(default="New conversation", max_length=255)


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    sources_json: str | None = None
    cost_usd: float | None = None
    latency_ms: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}


class ConversationDetail(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse]

    model_config = {"from_attributes": True}


# ── Usage Analytics ──

class UsageSummary(BaseModel):
    total_queries: int = 0
    total_documents: int = 0
    total_tokens_used: int = 0
    total_cost_usd: float = 0.0
    avg_latency_ms: float = 0.0
    avg_cost_per_query_usd: float = 0.0


class DailyUsage(BaseModel):
    date: str
    queries: int = 0
    tokens: int = 0
    cost_usd: float = 0.0


class UsageAnalytics(BaseModel):
    summary: UsageSummary
    daily_usage: list[DailyUsage]
    cost_by_operation: dict[str, float]
