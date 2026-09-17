from typing import Optional
from urllib.parse import urlparse, parse_qs
import re


def extract_video_id(url: str) -> Optional[str]:
    """Extract a YouTube video ID from common URL formats."""
    parsed = urlparse(url)
    host = parsed.netloc.lower().replace("www.", "")

    if host in {"youtube.com", "m.youtube.com"}:
        if parsed.path == "/watch":
            return parse_qs(parsed.query).get("v", [None])[0]

        if parsed.path.startswith("/shorts/"):
            return parsed.path.split("/shorts/", 1)[1].split("/", 1)[0]

        if parsed.path.startswith("/embed/"):
            return parsed.path.split("/embed/", 1)[1].split("/", 1)[0]

    if host == "youtu.be":
        return parsed.path.strip("/").split("/", 1)[0] or None

    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url.strip()):
        return url.strip()

    return None
