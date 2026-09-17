from fastapi import FastAPI
from app.api.transcript import router as transcript_router

app = FastAPI(
    title="YouTube Transcript API",
    version="0.3.0",
    description="Caption-first transcript API with local faster-whisper fallback."
)

app.include_router(transcript_router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
