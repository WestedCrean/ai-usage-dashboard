from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ai_usage_dashboard.database import get_db
from ai_usage_dashboard.models import AIModel
from ai_usage_dashboard.schemas import AIModelCreate, AIModelRead

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/", response_model=list[AIModelRead])
def list_models(db: Session = Depends(get_db)):
    return db.query(AIModel).all()


@router.post("/", response_model=AIModelRead, status_code=status.HTTP_201_CREATED)
def create_model(payload: AIModelCreate, db: Session = Depends(get_db)):
    model = AIModel(**payload.model_dump())
    db.add(model)
    try:
        db.commit()
        db.refresh(model)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A model with name '{payload.name}' already exists.",
        )
    return model
