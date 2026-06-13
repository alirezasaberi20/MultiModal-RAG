import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.api.deps import get_current_user
from app.config import get_settings
from app.db.database import get_db
from app.db.models import Conversation, Document, Message, UsageLog, User
from app.rag.pipeline import RAGPipeline
from app.schemas import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])
settings = get_settings()


def _check_has_ready_docs(db: Session, user: User) -> None:
    """Verify user has at least one ready document."""
    has_ready = (
        db.query(Document.id)
        .filter(Document.user_id == user.id, Document.status == "ready")
        .first()
    )
    if not has_ready:
        raise HTTPException(
            status_code=400,
            detail="No processed documents available. Upload a PDF and wait for processing.",
        )


def _get_explicit_document_ids(
    db: Session, user: User, requested_ids: list[int]
) -> list[int]:
    """Validate user-selected document IDs."""
    owned = (
        db.query(Document.id)
        .filter(
            Document.user_id == user.id,
            Document.id.in_(requested_ids),
            Document.status == "ready",
        )
        .all()
    )
    owned_ids = [row[0] for row in owned]
    if not owned_ids:
        raise HTTPException(
            status_code=400,
            detail="No ready documents found for the given document_ids.",
        )
    return owned_ids


@router.post("/query", response_model=ChatResponse)
def query_documents(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is not configured. Set it in your .env file.",
        )

    if payload.document_ids:
        document_ids = _get_explicit_document_ids(db, current_user, payload.document_ids)
    else:
        _check_has_ready_docs(db, current_user)
        document_ids = None

    pipeline = RAGPipeline(user_id=current_user.id)
    response = pipeline.query(query=payload.query, document_ids=document_ids)

    conversation_id = payload.conversation_id
    if conversation_id is None:
        title = payload.query[:80] + ("..." if len(payload.query) > 80 else "")
        conversation = Conversation(user_id=current_user.id, title=title)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        conversation_id = conversation.id
    else:
        conv = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        ).first()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=payload.query,
    )
    db.add(user_msg)

    assistant_msg = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=response.answer,
        sources_json=json.dumps([s.model_dump() for s in response.sources]),
        cost_usd=response.cost.estimated_cost_usd if response.cost else None,
        latency_ms=response.cost.latency_ms if response.cost else None,
        token_count=response.cost.total_tokens if response.cost else None,
    )
    db.add(assistant_msg)

    if response.cost and settings.cost_tracking_enabled:
        usage_log = UsageLog(
            user_id=current_user.id,
            operation="chat",
            model=settings.openai_chat_model,
            input_tokens=response.cost.chat_input_tokens + response.cost.embedding_tokens,
            output_tokens=response.cost.chat_output_tokens,
            total_tokens=response.cost.total_tokens,
            cost_usd=response.cost.estimated_cost_usd,
            latency_ms=response.cost.latency_ms,
        )
        db.add(usage_log)

    db.commit()

    response.conversation_id = conversation_id
    return response


@router.post("/query/stream")
async def stream_query(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is not configured.",
        )

    if payload.document_ids:
        document_ids = _get_explicit_document_ids(db, current_user, payload.document_ids)
    else:
        _check_has_ready_docs(db, current_user)
        document_ids = None

    pipeline = RAGPipeline(user_id=current_user.id)

    async def event_generator():
        full_answer = []
        for token in pipeline.stream_query(payload.query, document_ids):
            full_answer.append(token)
            yield {"event": "token", "data": json.dumps({"token": token})}

        yield {
            "event": "done",
            "data": json.dumps({"answer": "".join(full_answer)}),
        }

    return EventSourceResponse(event_generator())
