# YouTube Transcript API — faster-whisper

No OpenAI API key and no database.

Pipeline:

YouTube URL
    |
    +--> Try accessible captions
    |
    +--> If unavailable
             |
             +--> Obtain authorized audio
             |
             +--> faster-whisper (local)
             |
             +--> timestamped transcript

## Important

Use this only with videos/content you are authorized to process and in
compliance with applicable platform terms.

## Requirements

- Python 3.9+
- ffmpeg
- yt-dlp
- Enough RAM/storage for the selected Whisper model

## 1. Install ffmpeg

macOS with Homebrew:

```bash
brew install ffmpeg
```

## 2. Create virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3. Install packages

```bash
pip install -r requirements.txt
```

The first time faster-whisper loads a model, the model files are downloaded
automatically.

## 4. Start API

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

## 5. Test

```bash
curl -X POST "http://127.0.0.1:8000/api/transcript" -H "Content-Type: application/json" -d '{"url":"https://www.youtube.com/watch?v=YOUR_VIDEO_ID"}'
```

## Whisper configuration

Default:

```text
WHISPER_MODEL=small
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

For a faster CPU test you can use:

```bash
export WHISPER_MODEL=base
```

For supported NVIDIA GPU machines:

```bash
export WHISPER_DEVICE=cuda
export WHISPER_COMPUTE_TYPE=float16
```

## Current architecture

There is intentionally no database and no OpenAI API.

The endpoint returns:

```json
{
  "video_id": "abc123",
  "source": "faster_whisper",
  "language": "en",
  "segments": [
    {
      "start": 0.0,
      "end": 4.2,
      "text": "Today we are going to talk about AI."
    }
  ]
}
```

The timestamps will later be used by the AI clip-selection module.

## Next improvement

For long videos, move processing to a background job and add progress
tracking. Then add word-level timestamps and AI clip detection.
