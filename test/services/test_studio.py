"""Behavior and security checks for the replacement browser API."""

import json
import os
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from app import asgi
from app.config import config
from app.controllers.v1 import studio as controller
from app.models import const
from app.models.schema import VideoParams
from app.services import state, studio


@pytest.fixture
def client():
    with patch.dict(config.app, {"api_key": ""}):
        yield TestClient(asgi.app)


def test_bootstrap_settings_and_locale_do_not_expose_credentials(client):
    with patch.dict(
        config.app,
        {"openai_api_key": "secret-credential", "pexels_api_keys": ["secret-stock"]},
    ):
        bootstrap = client.get("/api/v1/studio/bootstrap")
        settings = client.get("/api/v1/studio/settings")
        assert bootstrap.status_code == settings.status_code == 200
        assert "secret-credential" not in settings.text + bootstrap.text
        assert "secret-stock" not in settings.text + bootstrap.text
        assert settings.json()["configured"]["app"]["openai_api_key"] is True
    assert client.get("/api/v1/studio/locales/pt").json()["Language"] == "Português"
    assert client.get("/api/v1/studio/locales/missing").status_code == 400


def test_settings_mask_credentials_embedded_in_urls(client):
    with (
        patch.dict(config.proxy, {"https": "http://user:password@proxy.local:8080"}),
        patch.dict(
            config.app, {"openai_base_url": "https://provider.local/v1?token=private"}
        ),
    ):
        response = client.get("/api/v1/studio/settings")
        assert (
            "user:password" not in response.text
            and "token=private" not in response.text
        )
        assert response.json()["sections"]["proxy"]["https"] == ""
        assert response.json()["configured"]["app"]["openai_base_url"]


def test_cookie_authentication_covers_native_media_and_revokes_on_key_change():
    client = TestClient(asgi.app)
    with patch.dict(config.app, {"api_key": "chave-é"}):
        assert client.get("/api/v1/studio/bootstrap").status_code == 401
        assert (
            client.post("/api/v1/studio/session", json={"key": "wrong"}).status_code
            == 401
        )
        response = client.post("/api/v1/studio/session", json={"key": "chave-é"})
        assert response.status_code == 200
        assert "httponly" in response.headers["set-cookie"].lower()
        assert client.get("/api/v1/studio/bootstrap").status_code == 200
        assert client.get("/api/v1/studio/previews/missing").status_code == 404
        with patch.dict(config.app, {"api_key": "changed"}):
            assert client.get("/api/v1/studio/bootstrap").status_code == 401
        assert (
            client.post(
                "/api/v1/studio/session",
                json={"key": "chave-é"},
                headers={"Origin": "https://untrusted.example"},
            ).status_code
            == 403
        )
        assert client.delete("/api/v1/studio/session").status_code == 200
        assert client.get("/api/v1/studio/bootstrap").status_code == 401


def test_settings_validate_before_updating_and_queue_defaults(client):
    with (
        patch.object(config, "update_config_nonblocking") as update,
        patch.object(config, "try_save_config", return_value=False),
    ):
        response = client.patch(
            "/api/v1/studio/settings",
            json={
                "ui": {
                    "tts_server": "kokoro",
                    "voice_mode": "tts",
                    "video_terms": None,
                    "subtitle_animation": "pop_spring",
                }
            },
        )
        assert response.status_code == 200 and response.json()["pending"]
        assert update.call_count == 4
        update.reset_mock()
        assert (
            client.patch(
                "/api/v1/studio/settings",
                json={"app": {"openai_api_key": "new", "not_a_setting": "bad"}},
            ).status_code
            == 400
        )
        update.assert_not_called()
        assert (
            client.patch(
                "/api/v1/studio/settings", json={"ui": {"video_materials": []}}
            ).status_code
            == 400
        )


def test_cookie_session_can_generate_script_and_terms_without_exposing_api_key():
    from app.controllers.v1 import llm as llm_controller

    client = TestClient(asgi.app)
    with patch.dict(config.app, {"api_key": "protected"}):
        assert (
            client.post("/api/v1/studio/session", json={"key": "protected"}).status_code
            == 200
        )
        with patch.object(
            llm_controller,
            "generate_video_script",
            return_value={"data": {"video_script": "result"}},
        ):
            assert (
                client.post(
                    "/api/v1/studio/scripts", json={"video_subject": "test"}
                ).json()["data"]["video_script"]
                == "result"
            )
        with patch.object(
            llm_controller,
            "generate_video_terms",
            return_value={"data": {"video_terms": ["term"]}},
        ):
            assert client.post(
                "/api/v1/studio/terms",
                json={"video_subject": "test", "video_script": "script"},
            ).json()["data"]["video_terms"] == ["term"]
        assert (
            client.post("/api/v1/scripts", json={"video_subject": "test"}).status_code
            == 401
        )


def test_presets_strip_private_paths_and_keep_subtitle_options(client):
    params = {
        "video_subject": "test",
        "subtitle_animation": "pop_spring",
        "video_materials": [{"url": "/secret/private.mp4"}],
        "custom_audio_file": "/secret/audio.wav",
    }
    exported = client.post("/api/v1/studio/presets/export", json=params)
    assert exported.status_code == 200
    assert "/secret/" not in exported.text
    restored = client.post("/api/v1/studio/presets/import", json=exported.json())
    assert restored.status_code == 200
    assert restored.json()["params"]["subtitle_animation"] == "pop_spring"
    assert restored.json()["params"]["video_materials"] is None
    assert (
        client.post(
            "/api/v1/studio/presets/import", json={"schema": "other"}
        ).status_code
        == 400
    )


def test_generation_uses_background_worker_and_rejects_server_paths(client):
    with patch.object(controller.webui_task, "submit_generation") as submit:
        response = client.post(
            "/api/v1/studio/generate",
            json={
                "params": {
                    "video_subject": "test",
                    "subtitle_enabled": False,
                    "voice_name": "no-voice",
                }
            },
        )
        assert response.status_code == 202
        assert submit.call_args.args[0] == response.json()["task_id"]
        assert submit.call_args.args[1].voice_name == "no-voice"
        for changes in (
            {"custom_audio_file": "/etc/passwd"},
            {"font_name": "../../config.toml", "subtitle_enabled": True},
            {
                "video_source": "local",
                "video_materials": [{"url": "../../config.toml"}],
            },
            {"video_clip_speed": 100},
        ):
            assert (
                client.post(
                    "/api/v1/studio/generate",
                    json={
                        "params": {
                            "video_subject": "test",
                            "subtitle_enabled": False,
                            **changes,
                        }
                    },
                ).status_code
                == 400
            )
        assert submit.call_count == 1


def test_paid_video_sources_require_confirmation_before_any_worker(client):
    with patch.object(controller.webui_task, "submit_generation") as submit:
        for source in (
            "wavespeed",
            "volcengine_seedance",
            "ofox",
            "metaso_minimax",
            "muapi",
        ):
            payload = {
                "params": {
                    "video_subject": "test",
                    "video_source": source,
                    "subtitle_enabled": False,
                }
            }
            assert (
                client.post("/api/v1/studio/generate", json=payload).status_code == 400
            )
            assert (
                client.post(
                    "/api/v1/studio/generate",
                    json={**payload, "paid_source_confirmed": True},
                ).status_code
                == 202
            )
        assert submit.call_count == 5


def test_full_preview_reuses_task_local_audio_and_not_pending_configuration(tmp_path):
    from app.services import voice

    params = VideoParams(
        video_subject="test",
        video_script="A complete narration.",
        voice_name="pt-BR-FranciscaNeural-Female",
    )
    maker = SimpleNamespace(subs=[])
    task_folder = tmp_path / "render"
    task_folder.mkdir()

    def speech(**kwargs):
        Path(kwargs["voice_file"]).write_bytes(b"mock-audio")
        return maker

    with (
        patch.object(studio.utils, "storage_dir", return_value=str(tmp_path)),
        patch.object(studio.utils, "task_dir", return_value=str(task_folder)),
        patch.object(voice, "tts", side_effect=speech),
        patch.object(voice, "get_audio_duration", return_value=3),
    ):
        preview = studio.preview(params, text=params.video_script, full=True)
        reused = studio.reusable_preview(preview["id"], params, "render")
        assert reused["audio_file"] == str(task_folder / "preview-audio.mp3")
        assert Path(reused["audio_file"]).read_bytes() == b"mock-audio"
        assert "audio_bytes" not in reused
        assert (
            studio.reusable_preview(
                preview["id"], params, "render", b"different-reference"
            )
            is None
        )
        with patch.object(
            config,
            "snapshot_config_with_pending",
            side_effect=lambda section: {**section, "pending-change": True},
        ):
            assert studio.reusable_preview(preview["id"], params, "render") is None
            second = studio.preview(params, text=params.video_script, full=True)
            assert (
                studio.get_preview(second["id"])["signature"]
                == studio.get_preview(preview["id"])["signature"]
            )
        studio._previews.pop(preview["id"], None)
        studio._previews.pop(second["id"], None)


def test_minimax_catalog_failure_keeps_configured_private_voice():
    from app.services import voice

    with (
        patch.dict(config.minimax_tts, {"voice_id": "private-clone"}),
        patch.object(
            voice, "get_minimax_voice_catalog", side_effect=ValueError("offline")
        ),
    ):
        assert "minimax:private-clone" in studio.voices("minimax-tts")


def test_optional_speech_errors_explain_selected_installation_without_loading_models(
    client,
):
    with patch("importlib.util.find_spec", return_value=None):
        params = VideoParams(
            video_subject="test", voice_name="pt-BR-FranciscaNeural-V2-Female"
        )
        with pytest.raises(ValueError, match="--extra azure-speech"):
            controller.check_speech_runtime(params)
        params.voice_name = "no-voice"
        with patch.dict(config.app, {"subtitle_provider": "whisper"}):
            with pytest.raises(ValueError, match="--extra whisper"):
                controller.check_speech_runtime(params, uploaded_narration=True)
        params.subtitle_enabled = False
        controller.check_speech_runtime(params, uploaded_narration=True)


@pytest.mark.skipif(
    os.environ.get("MPT_RENDER_SMOKE") != "1", reason="opt-in real FFmpeg render"
)
def test_real_local_upload_narration_render_and_download(client, tmp_path):
    """End-to-end engine check without keys, network, or paid provider calls."""
    video = tmp_path / "source.mp4"
    audio = tmp_path / "narration.wav"
    for target, arguments in (
        (
            video,
            [
                "-f",
                "lavfi",
                "-i",
                "color=c=green:s=480x480:d=2",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
            ],
        ),
        (audio, ["-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "2"]),
    ):
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", *arguments, str(target)],
            check=True,
        )

    def storage(sub_dir="", create=False):
        folder = tmp_path / "storage" / sub_dir
        if create:
            folder.mkdir(parents=True, exist_ok=True)
        return str(folder)

    def tasks(identifier=""):
        folder = Path(storage("tasks", True)) / identifier
        folder.mkdir(parents=True, exist_ok=True)
        return str(folder)

    with (
        patch.object(studio.utils, "storage_dir", side_effect=storage),
        patch.object(studio.utils, "task_dir", side_effect=tasks),
        patch.dict(
            config.app, {"upload_post_enabled": False, "upload_post_auto_upload": False}
        ),
    ):
        with video.open("rb") as source:
            media = client.post(
                "/api/v1/studio/uploads/material",
                files={"file": (video.name, source, "video/mp4")},
            )
        with audio.open("rb") as source:
            narration = client.post(
                "/api/v1/studio/uploads/narration",
                files={"file": (audio.name, source, "audio/wav")},
            )
        assert media.status_code == narration.status_code == 200
        response = client.post(
            "/api/v1/studio/generate",
            json={
                "params": {
                    "video_subject": "Local smoke test",
                    "video_script": "A local narration.",
                    "video_source": "local",
                    "video_materials": [{"url": media.json()["id"]}],
                    "video_aspect": "1:1",
                    "subtitle_enabled": False,
                    "bgm_type": "",
                    "n_threads": 1,
                },
                "narration_id": narration.json()["id"],
            },
        )
        assert response.status_code == 202
        identifier = response.json()["task_id"]
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            detail = client.get(f"/api/v1/studio/tasks/{identifier}").json()
            if detail.get("state") in {1, -1}:
                break
            time.sleep(0.2)
        assert detail.get("state") == 1, detail.get("error", detail)
        assert detail["video_files"]
        result = client.get(detail["video_files"][0]["url"])
        assert result.status_code == 200 and len(result.content) > 1000


def test_disk_history_files_ranges_and_busy_delete(client, tmp_path):
    folder = tmp_path / "historical-task"
    folder.mkdir()
    (folder / "final-1.mp4").write_bytes(b"0123456789")
    (folder / "script.json").write_text(
        json.dumps(
            {
                "params": {
                    "video_subject": "Old render",
                    "custom_audio_file": "/old/narration.mp3",
                },
                "script": "Generated narration",
                "search_terms": ["actual term"],
            }
        )
    )
    with (
        patch.object(studio.utils, "task_dir", return_value=str(tmp_path)),
        patch.object(state.state, "get_task", return_value=None),
    ):
        detail = client.get("/api/v1/studio/tasks/historical-task")
        assert detail.status_code == 200 and detail.json()["subject"] == "Old render"
        assert detail.json()["params"]["video_script"] == "Generated narration"
        assert detail.json()["params"]["video_terms"] == ["actual term"]
        assert detail.json()["params"]["custom_audio_file"] == "/old/narration.mp3"
        url = detail.json()["video_files"][0]["url"]
        assert client.get(url, headers={"Range": "bytes=2-5"}).content == b"2345"
        assert client.get(url, headers={"Range": "bytes=2-5"}).status_code == 206
        assert (
            client.get("/api/v1/studio/tasks").json()["tasks"][0]["subject"]
            == "Old render"
        )
        with patch.object(
            state.state, "get_task", return_value={"state": const.TASK_STATE_PROCESSING}
        ):
            assert (
                client.delete("/api/v1/studio/tasks/historical-task").status_code == 409
            )
        with patch.object(state.state, "delete_task") as delete:
            assert (
                client.delete("/api/v1/studio/tasks/historical-task").status_code == 200
            )
            delete.assert_called_once_with("historical-task")
            assert not folder.exists()


def test_task_symlinks_and_traversal_are_rejected(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "tasks"
    root.mkdir()
    (root / "linked").symlink_to(outside, target_is_directory=True)
    with patch.object(studio.utils, "task_dir", return_value=str(root)):
        for name in ("../outside", "linked", "..", "", "foo/bar"):
            with pytest.raises(ValueError):
                studio.task_path(name)
    assert outside.exists()


def test_paid_quote_requires_unchanged_inputs_account_and_confirmation():
    from app.services import loomloom

    settings = loomloom.LoomLoomSettings.from_mapping({"loomloom_api_token": "token"})
    entry = {
        "kind": "script",
        "backend": SimpleNamespace(settings=settings),
        "inputs": {"subject": "test"},
        "used": False,
    }
    studio._remember(studio._quotes, "test-quote", entry)
    with patch.dict(
        config.app,
        {"loomloom_api_token": "token", "loomloom_base_url": settings.base_url},
    ):
        with pytest.raises(ValueError):
            studio.confirmed_quote("test-quote", "script", entry["inputs"], False)
        with pytest.raises(ValueError):
            studio.confirmed_quote("test-quote", "script", {"subject": "changed"}, True)
        with patch.dict(config.app, {"loomloom_api_token": "other"}):
            with pytest.raises(ValueError):
                studio.confirmed_quote("test-quote", "script", entry["inputs"], True)
        assert studio.confirmed_quote("test-quote", "script", entry["inputs"], True)[
            "used"
        ]
        with pytest.raises(ValueError):
            studio.confirmed_quote("test-quote", "script", entry["inputs"], True)
    studio._quotes.pop("test-quote", None)


def test_loomloom_script_api_retry_reuses_idempotency_and_returns_candidates(client):
    from app.services import loomloom

    settings = loomloom.LoomLoomSettings.from_mapping(
        {"loomloom_api_token": "test-token"}
    )
    inputs = {
        "subject": "test",
        "candidate_count": 1,
        "language": "pt",
        "duration_seconds": 30,
        "style": "",
    }
    batch = loomloom.LoomLoomScriptBatch(({"subject": "test"},))
    quote = loomloom.LoomLoomQuote(
        "provider-quote", "listing-version", "USD", 1, 0, "0.00", batch.input_rows
    )
    execution = loomloom.LoomLoomExecution(
        "mock-run", "transaction", "completed", "listing-version"
    )
    backend = SimpleNamespace(
        settings=settings,
        prepare_script_batch=Mock(return_value=batch),
        quote=Mock(return_value=quote),
        execute=Mock(
            side_effect=[RuntimeError("temporary network failure"), execution]
        ),
        get_run=Mock(
            return_value=loomloom.LoomLoomRun("mock-run", "completed", 1, 1, 0, 0, "")
        ),
        get_script_results=Mock(
            return_value=loomloom.LoomLoomScriptBatchResult(
                (
                    loomloom.LoomLoomScriptCandidate(
                        0, "Generated candidate", ("forest",)
                    ),
                ),
                (),
            )
        ),
    )
    with (
        patch.dict(
            config.app,
            {
                "loomloom_api_token": settings.api_token,
                "loomloom_base_url": settings.base_url,
            },
        ),
        patch.object(loomloom, "LoomLoomScriptBackend", return_value=backend),
    ):
        quoted = client.post(
            "/api/v1/studio/loomloom/quote", json={"kind": "script", "inputs": inputs}
        )
        assert quoted.status_code == 200 and "input_rows" not in quoted.json()
        payload = {
            "kind": "script",
            "inputs": inputs,
            "quote_id": quoted.json()["id"],
            "confirmed": False,
        }
        assert (
            client.post("/api/v1/studio/loomloom/scripts", json=payload).status_code
            == 400
        )
        backend.execute.assert_not_called()
        payload["confirmed"] = True
        assert (
            client.post("/api/v1/studio/loomloom/scripts", json=payload).status_code
            == 409
        )
        assert (
            client.post("/api/v1/studio/loomloom/scripts", json=payload).status_code
            == 202
        )
        assert (
            backend.execute.call_args_list[0].kwargs
            == backend.execute.call_args_list[1].kwargs
        )
        assert (
            client.post("/api/v1/studio/loomloom/scripts", json=payload).status_code
            == 400
        )
        result = client.get("/api/v1/studio/loomloom/scripts/mock-run")
        assert (
            result.json()["results"]["candidates"][0]["script"] == "Generated candidate"
        )
        assert client.get("/api/v1/studio/loomloom/scripts/missing").status_code == 404
        studio._quotes.pop(quoted.json()["id"], None)
        controller._runs.pop("mock-run", None)
