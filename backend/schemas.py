import json
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator


class VideoImport(BaseModel):
    url: str


class VideoOut(BaseModel):
    id: int
    url: str
    bvid: str
    title: str
    description: str
    duration: int
    cid: int = 0
    source: str = "bilibili"
    created_at: datetime


class NoteOut(BaseModel):
    id: int
    video_id: int
    summary: str
    key_points: list[str]
    subtitle_text: str = ""
    cleaned_subtitle: str = ""
    translated_subtitle: str = ""
    usage: dict = {}
    created_at: datetime
    updated_at: datetime

    @field_validator("key_points", mode="before")
    @classmethod
    def parse_key_points(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

    @field_validator("usage", mode="before")
    @classmethod
    def parse_usage(cls, v):
        if isinstance(v, str):
            return json.loads(v) if v else {}
        return v or {}
        if isinstance(v, str):
            return json.loads(v)
        return v


class CardOut(BaseModel):
    id: int
    note_id: int
    question: str
    answer: str
    ease_factor: float
    interval: int
    repetitions: int
    next_review: datetime
    created_at: datetime


class GenerateIn(BaseModel):
    text: str | None = None


class ReviewIn(BaseModel):
    rating: int


class StatsOut(BaseModel):
    total_videos: int
    total_cards: int
    due_cards: int
    total_reviews: int
