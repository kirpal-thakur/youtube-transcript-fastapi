import glob
import os
import shutil
import tempfile
from typing import Any, Dict

from youtube_transcript_api import YouTubeTranscriptApi
from faster_whisper import WhisperModel
from yt_dlp import YoutubeDL


# -----------------------------
# Whisper configuration
# -----------------------------

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

_model = None


def get_whisper_model():
    """Load Whisper once and reuse it."""
    global _model

    if _model is None:
        _model = WhisperModel(
            WHISPER_MODEL,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
        )

    return _model


# -----------------------------
# YouTube captions
# -----------------------------

def get_caption_transcript(video_id: str) -> Dict[str, Any]:
    """Try YouTube captions first."""

    api = YouTubeTranscriptApi()
    transcript = api.fetch(video_id)

    segments = []

    for item in transcript:
        start = float(item.start)
        duration = float(item.duration)

        text = item.text.strip()

        if text:
            segments.append({
                "start": start,
                "end": start + duration,
                "text": text,
            })

    return {
        "video_id": video_id,
        "source": "youtube_captions",
        "language": getattr(transcript, "language_code", None),
        "segments": segments,
    }


# -----------------------------
# Audio download
# -----------------------------

def download_audio(video_id: str, output_dir: str) -> str:
    """
    Download audio using the yt-dlp Python API.

    We intentionally do NOT convert to MP3 here.
    Faster-Whisper/PyAV can decode common audio formats directly.

    This avoids depending on the yt-dlp executable being in PATH
    and avoids requiring FFmpeg just for transcription.
    """

    url = "https://www.youtube.com/watch?v={}".format(video_id)

    output_template = os.path.join(
        output_dir,
        "audio.%(ext)s"
    )

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": False,
        "no_warnings": False,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    except Exception as exc:
        raise ValueError(
            "Could not obtain audio with yt-dlp: {}".format(str(exc))
        )

    # Find the downloaded audio file.
    files = glob.glob(
        os.path.join(output_dir, "audio.*")
    )

    files = [
        path for path in files
        if not path.endswith(".part")
    ]

    if not files:
        raise ValueError(
            "yt-dlp completed but no audio file was produced."
        )

    return files[0]


# -----------------------------
# Faster-Whisper
# -----------------------------

def transcribe_with_whisper(audio_path: str) -> Dict[str, Any]:
    """Transcribe audio using Faster-Whisper."""

    model = get_whisper_model()

    segments_iter, info = model.transcribe(
        audio_path,
        beam_size=5,
        vad_filter=False,
        task="transcribe",
    )

    segments = []

    for segment in segments_iter:
        text = segment.text.strip()

        if text:
            segments.append({
                "start": float(segment.start),
                "end": float(segment.end),
                "text": text,
            })

    return {
        "source": "faster_whisper",
        "language": getattr(info, "language", None),
        "segments": segments,
    }


# -----------------------------
# Main transcript pipeline
# -----------------------------

def get_transcript(video_id: str) -> Dict[str, Any]:
    """
    Transcript pipeline:

    1. Try YouTube captions.
    2. If captions unavailable, download audio with yt-dlp.
    3. Transcribe with Faster-Whisper.
    """

    # First attempt: YouTube captions
    try:
        return get_caption_transcript(video_id)

    except Exception:
        # No accessible captions.
        pass

    # Fallback: local/worker transcription
    temp_dir = tempfile.mkdtemp(
        prefix="yt_transcript_"
    )

    try:
        audio_path = download_audio(
            video_id,
            temp_dir
        )

        result = transcribe_with_whisper(
            audio_path
        )

        result["video_id"] = video_id

        return result

    finally:
        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )