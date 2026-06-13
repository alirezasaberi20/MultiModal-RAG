from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models import Document, UsageLog, User
from app.schemas import DailyUsage, UsageAnalytics, UsageSummary

router = APIRouter(prefix="/usage", tags=["Usage Analytics"])


@router.get("/summary", response_model=UsageSummary)
def get_usage_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logs = db.query(UsageLog).filter(UsageLog.user_id == current_user.id).all()
    doc_count = db.query(Document).filter(Document.user_id == current_user.id).count()

    total_queries = len([l for l in logs if l.operation == "chat"])
    total_tokens = sum(l.total_tokens for l in logs)
    total_cost = sum(l.cost_usd for l in logs)
    avg_latency = sum(l.latency_ms for l in logs) / len(logs) if logs else 0.0
    avg_cost = total_cost / total_queries if total_queries else 0.0

    return UsageSummary(
        total_queries=total_queries,
        total_documents=doc_count,
        total_tokens_used=total_tokens,
        total_cost_usd=round(total_cost, 6),
        avg_latency_ms=round(avg_latency, 1),
        avg_cost_per_query_usd=round(avg_cost, 6),
    )


@router.get("/analytics", response_model=UsageAnalytics)
def get_usage_analytics(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cutoff = datetime.now(UTC) - timedelta(days=days)

    logs = (
        db.query(UsageLog)
        .filter(UsageLog.user_id == current_user.id, UsageLog.created_at >= cutoff)
        .all()
    )
    doc_count = db.query(Document).filter(Document.user_id == current_user.id).count()

    total_queries = len([l for l in logs if l.operation == "chat"])
    total_tokens = sum(l.total_tokens for l in logs)
    total_cost = sum(l.cost_usd for l in logs)
    avg_latency = sum(l.latency_ms for l in logs) / len(logs) if logs else 0.0
    avg_cost = total_cost / total_queries if total_queries else 0.0

    summary = UsageSummary(
        total_queries=total_queries,
        total_documents=doc_count,
        total_tokens_used=total_tokens,
        total_cost_usd=round(total_cost, 6),
        avg_latency_ms=round(avg_latency, 1),
        avg_cost_per_query_usd=round(avg_cost, 6),
    )

    daily_map: dict[str, DailyUsage] = {}
    for log in logs:
        day = log.created_at.strftime("%Y-%m-%d")
        if day not in daily_map:
            daily_map[day] = DailyUsage(date=day)
        entry = daily_map[day]
        if log.operation == "chat":
            entry.queries += 1
        entry.tokens += log.total_tokens
        entry.cost_usd = round(entry.cost_usd + log.cost_usd, 6)

    daily_usage = sorted(daily_map.values(), key=lambda d: d.date)

    cost_by_op: dict[str, float] = {}
    for log in logs:
        cost_by_op[log.operation] = round(
            cost_by_op.get(log.operation, 0.0) + log.cost_usd, 6
        )

    return UsageAnalytics(
        summary=summary,
        daily_usage=daily_usage,
        cost_by_operation=cost_by_op,
    )
