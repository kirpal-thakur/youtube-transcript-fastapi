from fastapi import APIRouter, HTTPException

from app.schemas.transcript import TranscriptRequest, TranscriptResponse
from app.services.youtube import extract_video_id
from app.services.transcript import get_transcript

router = APIRouter(tags=["transcript"])


@router.post("/transcript", response_model=TranscriptResponse)
def transcript(request: TranscriptRequest):
    video_id = extract_video_id(str(request.url))

    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")

    try:
        return get_transcript(video_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Transcript processing failed: {}".format(str(exc))
        )
