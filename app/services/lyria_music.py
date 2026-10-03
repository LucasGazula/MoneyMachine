"""Google Lyria 3.5 background music through the Gemini Interactions API."""

import base64
import binascii
import json
import math
import os
import tempfile
from pathlib import Path

import requests

from app.config import config
from app.services import bgm


API_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
MAX_RESPONSE_BYTES = 70 * 1024 * 1024
MAX_AUDIO_BYTES = 50 * 1024 * 1024


class LyriaMusicError(RuntimeError):
    pass


def get_api_key() -> str:
    return str(config.app.get("gemini_api_key", "") or "").strip() or os.getenv(
        "GEMINI_API_KEY", ""
    ).strip()


def is_enabled() -> bool:
    return bool(get_api_key())


def generate_bgm(
    video_path: str, output_path: str, video_duration: float, prompt: str = ""
) -> str:
    """Generate a prompt-based MP3; the Google endpoint does not accept video input."""
    api_key = get_api_key()
    if not api_key:
        raise LyriaMusicError("Google Gemini API key is required for Lyria music")
    if not os.path.isfile(video_path):
        raise LyriaMusicError("Lyria input video does not exist")
    try:
        duration = float(video_duration)
    except (TypeError, ValueError) as exc:
        raise LyriaMusicError("Lyria video duration is invalid") from exc
    if not math.isfinite(duration) or duration <= 0:
        raise LyriaMusicError("Lyria video duration is invalid")
    prompt = str(prompt or "").strip()
    if not prompt or len(prompt) > 2000:
        raise LyriaMusicError("Lyria music prompt must contain 1 to 2000 characters")

    try:
        with requests.post(
            API_URL,
            headers={"x-goog-api-key": api_key},
            json={
                "model": "lyria-3.5",
                "input": f"Create music lasting about {duration:.0f} seconds. {prompt}",
            },
            timeout=(15, 600),
            stream=True,
        ) as response:
            if not response.ok:
                raise LyriaMusicError(
                    f"Google Lyria request failed (HTTP {response.status_code})"
                )
            payload = bytearray()
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if len(payload) + len(chunk) > MAX_RESPONSE_BYTES:
                    raise LyriaMusicError("Google Lyria response is too large")
                payload.extend(chunk)
    except requests.RequestException as exc:
        raise LyriaMusicError(f"Google Lyria request failed: {exc}") from exc

    try:
        interaction = json.loads(payload)
        audio_data = next(
            block["data"]
            for step in interaction["steps"]
            if step.get("type") == "model_output"
            for block in step.get("content", [])
            if block.get("type") == "audio"
        )
        if len(audio_data) > (MAX_AUDIO_BYTES + 2) // 3 * 4:
            raise LyriaMusicError("Google Lyria audio is too large")
        audio = base64.b64decode(audio_data, validate=True)
        if not audio or len(audio) > MAX_AUDIO_BYTES:
            raise LyriaMusicError("Google Lyria audio is empty or too large")
    except (AttributeError, KeyError, TypeError, ValueError, StopIteration, binascii.Error) as exc:
        raise LyriaMusicError("Google Lyria returned invalid audio") from exc

    temp_path = ""
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=".lyria-", suffix=".mp3",
            dir=Path(output_path).parent, delete=False,
        ) as temporary:
            temp_path = temporary.name
            temporary.write(audio)
        bgm.validate_audio_file(temp_path)
        os.replace(temp_path, output_path)
        return output_path
    except (OSError, bgm.BgmUploadError, bgm.BgmServiceError) as exc:
        raise LyriaMusicError(f"Google Lyria audio could not be saved: {exc}") from exc
    finally:
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)
