from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from models import Video, ReviewCard, ReviewLog
from schemas import StatsOut

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", response_model=StatsOut)
def stats(db: Session = Depends(get_db)):
    now = datetime.now()
    total_videos = db.query(Video).count()
    total_cards = db.query(ReviewCard).count()
    due_cards = db.query(ReviewCard).filter(ReviewCard.next_review <= now).count()
    total_reviews = db.query(ReviewLog).count()
    return StatsOut(
        total_videos=total_videos,
        total_cards=total_cards,
        due_cards=due_cards,
        total_reviews=total_reviews,
    )
