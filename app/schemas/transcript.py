from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class TranscriptRequest(BaseModel):
    url: HttpUrl = Field(..., description="YouTube video URL")


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str


class TranscriptResponse(BaseModel):
    video_id: str
    source: str
    language: Optional[str] = None
    segments: List[TranscriptSegment]
