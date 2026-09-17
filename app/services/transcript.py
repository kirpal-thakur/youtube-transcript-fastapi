import os
import shutil
import subprocess
import tempfile
from typing import Any, Dict

from youtube_transcript_api import YouTubeTranscriptApi
from faster_whisper import WhisperModel


# Small is a good starting point for local development.
# Change to "medium", "large-v3", etc. later when hardware allows.
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")

# "cpu" works on a normal Mac/PC.
# For a supported NVIDIA GPU, set WHISPER_DEVICE=cuda.
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")

# int8 is efficient for CPU inference.
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

_model = None


def get_whisper_model():
    """Load the Whisper model once and reuse it between requests."""
    global _model

    if _model is None:
        _model = WhisperModel(
            WHISPER_MODEL,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
        )

    return _model


def get_caption_transcript(video_id: str) -> Dict[str, Any]:
    """Try an accessible YouTube caption track first."""
    api = YouTubeTranscriptApi()
    transcript = api.fetch(video_id)

    segments = []

    for item in transcript:
        start = float(item.start)
        duration = float(item.duration)

        segments.append({
            "start": start,
            "end": start + duration,
            "text": item.text.strip(),
        })

    return {
        "video_id": video_id,
        "source": "youtube_captions",
        "language": getattr(transcript, "language_code", None),
        "segments": segments,
    }


def download_audio(video_id: str, output_dir: str) -> str:
    """
    Obtain audio for authorized content using yt-dlp.

    Requires yt-dlp and ffmpeg to be installed.
    """
    output_template = os.path.join(output_dir, "audio.%(ext)s")

    command = [
        "yt-dlp",
        "--no-playlist",
        "-x",
        "--audio-format", "mp3",
        "--audio-quality", "64K",
        "-o", output_template,
        "https://www.youtube.com/watch?v={}".format(video_id),
    ]

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=1800,
        )
    except FileNotFoundError:
        raise ValueError("yt-dlp is not installed. Run: pip install yt-dlp")
    except subprocess.TimeoutExpired:
        raise ValueError("Audio download timed out.")

    if result.returncode != 0:
        raise ValueError(
            "Could not obtain audio. Make sure you are authorized to process "
            "the content and that yt-dlp/ffmpeg can access it.\n{}"
            .format(result.stderr[-2000:])
        )

    audio_path = os.path.join(output_dir, "audio.mp3")

    if not os.path.exists(audio_path):
        raise ValueError("Audio extraction did not produce an MP3 file.")

    return audio_path


def transcribe_with_whisper(audio_path: str) -> Dict[str, Any]:
    """Transcribe audio locally with faster-whisper."""
    model = get_whisper_model()

    segments_iter, info = model.transcribe(
        audio_path,
        beam_size=5,
        vad_filter=True,
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


def get_transcript(video_id: str) -> Dict[str, Any]:
    """
    Transcript pipeline:
      1. Try accessible captions.
      2. If unavailable, obtain authorized audio.
      3. Transcribe locally with faster-whisper.
    """
    try:
        return get_caption_transcript(video_id)
    except Exception:
        # Caption failure intentionally triggers local STT fallback.
        pass

    temp_dir = tempfile.mkdtemp(prefix="yt_transcript_")

    try:
        audio_path = download_audio(video_id, temp_dir)
        result = transcribe_with_whisper(audio_path)
        result["video_id"] = video_id
        return result
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
