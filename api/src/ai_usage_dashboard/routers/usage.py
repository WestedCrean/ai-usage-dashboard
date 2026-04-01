from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from ai_usage_dashboard.database import get_db
from ai_usage_dashboard.models import AIModel, Project, UsageRecord
from ai_usage_dashboard.schemas import UsageRecordCreate, UsageRecordRead, UsageSummary

router = APIRouter(prefix="/usage", tags=["usage"])


def _apply_filters(
    query,
    model_id: int | None,
    project_id: int | None,
    team: str | None,
    from_ts: datetime | None,
    to_ts: datetime | None,
    db: Session,
):
    if model_id is not None:
        query = query.filter(UsageRecord.model_id == model_id)
    if project_id is not None:
        query = query.filter(UsageRecord.project_id == project_id)
    if team is not None:
        query = query.join(Project, UsageRecord.project_id == Project.id).filter(
            Project.team == team
        )
    if from_ts is not None:
        query = query.filter(UsageRecord.timestamp >= from_ts)
    if to_ts is not None:
        query = query.filter(UsageRecord.timestamp <= to_ts)
    return query


@router.post("/", response_model=UsageRecordRead, status_code=status.HTTP_201_CREATED)
def create_usage_record(payload: UsageRecordCreate, db: Session = Depends(get_db)):
    ai_model = db.query(AIModel).filter(AIModel.id == payload.model_id).first()
    if ai_model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AIModel with id {payload.model_id} not found.",
        )

    cost = (
        payload.input_tokens * ai_model.cost_per_input_token
        + payload.output_tokens * ai_model.cost_per_output_token
    )

    data = payload.model_dump()
    if data["timestamp"] is None:
        del data["timestamp"]  # let the model default kick in

    record = UsageRecord(**data, cost=cost)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/summary", response_model=UsageSummary)
def get_usage_summary(
    model_id: int | None = Query(default=None),
    project_id: int | None = Query(default=None),
    team: str | None = Query(default=None),
    from_ts: datetime | None = Query(default=None),
    to_ts: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(UsageRecord)
    query = _apply_filters(query, model_id, project_id, team, from_ts, to_ts, db)
    records = query.all()

    total_calls = len(records)
    if total_calls == 0:
        return UsageSummary(
            total_calls=0,
            total_input_tokens=0,
            total_output_tokens=0,
            total_cost=0.0,
            avg_latency_ms=None,
            success_rate=0.0,
        )

    total_input_tokens = sum(r.input_tokens for r in records)
    total_output_tokens = sum(r.output_tokens for r in records)
    total_cost = sum(r.cost for r in records)

    latencies = [r.latency_ms for r in records if r.latency_ms is not None]
    avg_latency_ms = sum(latencies) / len(latencies) if latencies else None

    success_count = sum(1 for r in records if r.success)
    success_rate = success_count / total_calls

    return UsageSummary(
        total_calls=total_calls,
        total_input_tokens=total_input_tokens,
        total_output_tokens=total_output_tokens,
        total_cost=total_cost,
        avg_latency_ms=avg_latency_ms,
        success_rate=success_rate,
    )


@router.get("/", response_model=list[UsageRecordRead])
def list_usage_records(
    model_id: int | None = Query(default=None),
    project_id: int | None = Query(default=None),
    team: str | None = Query(default=None),
    from_ts: datetime | None = Query(default=None),
    to_ts: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(UsageRecord)
    query = _apply_filters(query, model_id, project_id, team, from_ts, to_ts, db)
    return query.offset(offset).limit(limit).all()
