from datetime import datetime
from sqlalchemy.orm import Session
from models import Note, ReviewCard


def create_cards_from_notes(note: Note, cards_data: list[dict], db: Session) -> list[ReviewCard]:
    cards = []
    for card_data in cards_data:
        card = ReviewCard(
            note_id=note.id,
            question=card_data["question"],
            answer=card_data["answer"],
            next_review=datetime.now(),
        )
        db.add(card)
        cards.append(card)
    db.commit()
    return cards


def get_due_cards(db: Session) -> list[ReviewCard]:
    now = datetime.now()
    return db.query(ReviewCard).filter(ReviewCard.next_review <= now).all()
