from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import ReviewCard, ReviewLog, Note
from schemas import CardOut, ReviewIn
from services.sm2 import sm2_review

router = APIRouter(prefix="/api/cards", tags=["cards"])


@router.get("", response_model=list[CardOut])
def list_cards(db: Session = Depends(get_db)):
    return db.query(ReviewCard).order_by(ReviewCard.next_review).all()


@router.get("/due", response_model=list[CardOut])
def due_cards(db: Session = Depends(get_db)):
    now = datetime.now()
    return db.query(ReviewCard).filter(ReviewCard.next_review <= now).all()


@router.get("/video/{video_id}", response_model=list[CardOut])
def video_cards(video_id: int, db: Session = Depends(get_db)):
    return db.query(ReviewCard).join(Note).filter(Note.video_id == video_id).all()


@router.get("/due/{video_id}", response_model=list[CardOut])
def due_cards_by_video(video_id: int, db: Session = Depends(get_db)):
    now = datetime.now()
    return db.query(ReviewCard).join(Note).filter(
        Note.video_id == video_id, ReviewCard.next_review <= now
    ).all()


@router.post("/{card_id}/review", response_model=CardOut)
def review_card(card_id: int, data: ReviewIn, db: Session = Depends(get_db)):
    card = db.query(ReviewCard).filter(ReviewCard.id == card_id).first()
    if not card:
        raise HTTPException(404, "Card not found")

    result = sm2_review(card.ease_factor, card.interval, card.repetitions, data.rating)

    card.ease_factor = result["ease_factor"]
    card.interval = result["interval"]
    card.repetitions = result["repetitions"]
    card.next_review = result["next_review"]

    log = ReviewLog(card_id=card_id, rating=data.rating, reviewed_at=datetime.now())
    db.add(log)
    db.commit()
    db.refresh(card)
    return card


@router.delete("/{card_id}")
def delete_card(card_id: int, db: Session = Depends(get_db)):
    card = db.query(ReviewCard).filter(ReviewCard.id == card_id).first()
    if not card:
        raise HTTPException(404, "Card not found")
    db.query(ReviewLog).filter(ReviewLog.card_id == card_id).delete()
    db.delete(card)
    db.commit()
    return {"ok": True}


@router.delete("/video/{video_id}")
def clear_video_cards(video_id: int, db: Session = Depends(get_db)):
    cards = db.query(ReviewCard).join(Note).filter(Note.video_id == video_id).all()
    for card in cards:
        db.query(ReviewLog).filter(ReviewLog.card_id == card.id).delete()
        db.delete(card)
    db.commit()
    return {"ok": True, "deleted": len(cards)}


@router.delete("")
def clear_all_cards(db: Session = Depends(get_db)):
    db.query(ReviewLog).delete()
    count = db.query(ReviewCard).count()
    db.query(ReviewCard).delete()
    db.commit()
    return {"ok": True, "deleted": count}
