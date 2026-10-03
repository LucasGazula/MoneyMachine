import base64
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services import lyria_music


class Response:
    ok = True
    status_code = 200

    def __init__(self, audio):
        self.payload = json.dumps({
            "steps": [{"type": "model_output", "content": [
                {"type": "text", "text": "lyrics"},
                {"type": "audio", "data": base64.b64encode(audio).decode()},
            ]}],
        }).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def iter_content(self, chunk_size):
        yield self.payload


def test_lyria_sends_official_request_and_replaces_validated_audio(tmp_path):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"video")
    output = tmp_path / "music.mp3"
    output.write_bytes(b"previous")
    with (
        patch.object(lyria_music, "get_api_key", return_value="test-key"),
        patch.object(lyria_music.requests, "post", return_value=Response(b"ID3test")) as post,
        patch.object(lyria_music.bgm, "validate_audio_file") as validate,
    ):
        assert lyria_music.generate_bgm(str(video), str(output), 45, "warm piano") == str(output)
    assert output.read_bytes() == b"ID3test"
    assert Path(validate.call_args.args[0]).parent == tmp_path
    assert post.call_args.args[0] == lyria_music.API_URL
    assert post.call_args.kwargs["headers"] == {"x-goog-api-key": "test-key"}
    assert post.call_args.kwargs["json"] == {
        "model": "lyria-3.5",
        "input": "Create music lasting about 45 seconds. warm piano",
    }


def test_lyria_rejects_missing_audio_without_replacing_existing_file(tmp_path):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"video")
    output = tmp_path / "music.mp3"
    output.write_bytes(b"previous")
    response = Response(b"audio")
    response.payload = b'{"steps": []}'
    with (
        patch.object(lyria_music, "get_api_key", return_value="test-key"),
        patch.object(lyria_music.requests, "post", return_value=response),
        pytest.raises(lyria_music.LyriaMusicError, match="invalid audio"),
    ):
        lyria_music.generate_bgm(str(video), str(output), 45, "warm piano")
    assert output.read_bytes() == b"previous"
