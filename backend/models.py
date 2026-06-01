from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from database import Base


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, nullable=False)
    bvid = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    duration = Column(Integer, default=0)
    cid = Column(Integer, default=0)
    source = Column(String, default="bilibili")
    created_at = Column(DateTime, default=datetime.now)


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    summary = Column(Text, default="")
    key_points = Column(Text, default="[]")
    subtitle_text = Column(Text, default="")
    cleaned_subtitle = Column(Text, default="")
    translated_subtitle = Column(Text, default="")
    usage = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class ReviewCard(Base):
    __tablename__ = "review_cards"

    id = Column(Integer, primary_key=True, index=True)
    note_id = Column(Integer, ForeignKey("notes.id"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    ease_factor = Column(Float, default=2.5)
    interval = Column(Integer, default=0)
    repetitions = Column(Integer, default=0)
    next_review = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)


class ReviewLog(Base):
    __tablename__ = "review_logs"

    id = Column(Integer, primary_key=True, index=True)
    card_id = Column(Integer, ForeignKey("review_cards.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    reviewed_at = Column(DateTime, default=datetime.now)
