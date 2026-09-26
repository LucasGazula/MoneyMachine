"""Behavior and security checks for the replacement browser API."""

import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app import asgi
from app.config import config
from app.controllers.v1 import studio as controller
from app.models import const
from app.services import state, studio


@pytest.fixture
def client():
    with patch.dict(config.app, {"api_key": ""}):
        yield TestClient(asgi.app)


def test_bootstrap_settings_and_locale_do_not_expose_credentials(client):
    with patch.dict(config.app, {"openai_api_key": "secret-credential", "pexels_api_keys": ["secret-stock"]}):
        bootstrap = client.get("/api/v1/studio/bootstrap")
        settings = client.get("/api/v1/studio/settings")
        assert bootstrap.status_code == settings.status_code == 200
        assert "secret-credential" not in settings.text + bootstrap.text
        assert "secret-stock" not in settings.text + bootstrap.text
        assert settings.json()["configured"]["app"]["openai_api_key"] is True
    assert client.get("/api/v1/studio/locales/pt").json()["Language"] == "Português"
    assert client.get("/api/v1/studio/locales/missing").status_code == 400


def test_cookie_authentication_covers_native_media_and_revokes_on_key_change():
    client = TestClient(asgi.app)
    with patch.dict(config.app, {"api_key": "chave-é"}):
        assert client.get("/api/v1/studio/bootstrap").status_code == 401
        assert client.post("/api/v1/studio/session", json={"key": "wrong"}).status_code == 401
        response = client.post("/api/v1/studio/session", json={"key": "chave-é"})
        assert response.status_code == 200
        assert "httponly" in response.headers["set-cookie"].lower()
        assert client.get("/api/v1/studio/bootstrap").status_code == 200
        assert client.get("/api/v1/studio/previews/missing").status_code == 404
        with patch.dict(config.app, {"api_key": "changed"}):
            assert client.get("/api/v1/studio/bootstrap").status_code == 401
        assert client.post("/api/v1/studio/session", json={"key": "chave-é"}, headers={"Origin": "https://untrusted.example"}).status_code == 403
        assert client.delete("/api/v1/studio/session").status_code == 200
        assert client.get("/api/v1/studio/bootstrap").status_code == 401


def test_settings_validate_before_updating_and_queue_defaults(client):
    with patch.object(config, "update_config_nonblocking") as update, patch.object(config, "try_save_config", return_value=False):
        response = client.patch("/api/v1/studio/settings", json={"ui": {"tts_server": "kokoro", "voice_mode": "tts", "video_terms": None, "subtitle_animation": "pop_spring"}})
        assert response.status_code == 200 and response.json()["pending"]
        assert update.call_count == 4
        update.reset_mock()
        assert client.patch("/api/v1/studio/settings", json={"app": {"openai_api_key": "new", "not_a_setting": "bad"}}).status_code == 400
        update.assert_not_called()
        assert client.patch("/api/v1/studio/settings", json={"ui": {"video_materials": []}}).status_code == 400


def test_presets_strip_private_paths_and_keep_subtitle_options(client):
    params = {"video_subject": "test", "subtitle_animation": "pop_spring", "video_materials": [{"url": "/secret/private.mp4"}], "custom_audio_file": "/secret/audio.wav"}
    exported = client.post("/api/v1/studio/presets/export", json=params)
    assert exported.status_code == 200
    assert "/secret/" not in exported.text
    restored = client.post("/api/v1/studio/presets/import", json=exported.json())
    assert restored.status_code == 200
    assert restored.json()["params"]["subtitle_animation"] == "pop_spring"
    assert restored.json()["params"]["video_materials"] is None
    assert client.post("/api/v1/studio/presets/import", json={"schema": "other"}).status_code == 400


def test_generation_uses_background_worker_and_rejects_server_paths(client):
    with patch.object(controller.webui_task, "submit_generation") as submit:
        response = client.post("/api/v1/studio/generate", json={"params": {"video_subject": "test", "subtitle_enabled": False, "voice_name": "no-voice"}})
        assert response.status_code == 202
        assert submit.call_args.args[0] == response.json()["task_id"]
        assert submit.call_args.args[1].voice_name == "no-voice"
        for changes in ({"custom_audio_file": "/etc/passwd"}, {"font_name": "../../config.toml", "subtitle_enabled": True}, {"video_source": "local", "video_materials": [{"url": "../../config.toml"}]}, {"video_clip_speed": 100}):
            assert client.post("/api/v1/studio/generate", json={"params": {"video_subject": "test", "subtitle_enabled": False, **changes}}).status_code == 400
        assert submit.call_count == 1


def test_disk_history_files_ranges_and_busy_delete(client, tmp_path):
    folder = tmp_path / "historical-task"
    folder.mkdir()
    (folder / "final-1.mp4").write_bytes(b"0123456789")
    (folder / "script.json").write_text(json.dumps({"params": {"video_subject": "Old render"}}))
    with patch.object(studio.utils, "task_dir", return_value=str(tmp_path)), patch.object(state.state, "get_task", return_value=None):
        detail = client.get("/api/v1/studio/tasks/historical-task")
        assert detail.status_code == 200 and detail.json()["subject"] == "Old render"
        url = detail.json()["video_files"][0]["url"]
        assert client.get(url, headers={"Range": "bytes=2-5"}).content == b"2345"
        assert client.get(url, headers={"Range": "bytes=2-5"}).status_code == 206
        assert client.get("/api/v1/studio/tasks").json()["tasks"][0]["subject"] == "Old render"
        with patch.object(state.state, "get_task", return_value={"state": const.TASK_STATE_PROCESSING}):
            assert client.delete("/api/v1/studio/tasks/historical-task").status_code == 409
        with patch.object(state.state, "delete_task") as delete:
            assert client.delete("/api/v1/studio/tasks/historical-task").status_code == 200
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
    entry = {"kind": "script", "backend": SimpleNamespace(settings=settings), "inputs": {"subject": "test"}, "used": False}
    studio._remember(studio._quotes, "test-quote", entry)
    with patch.dict(config.app, {"loomloom_api_token": "token", "loomloom_base_url": settings.base_url}):
        with pytest.raises(ValueError):
            studio.confirmed_quote("test-quote", "script", entry["inputs"], False)
        with pytest.raises(ValueError):
            studio.confirmed_quote("test-quote", "script", {"subject": "changed"}, True)
        with patch.dict(config.app, {"loomloom_api_token": "other"}):
            with pytest.raises(ValueError):
                studio.confirmed_quote("test-quote", "script", entry["inputs"], True)
        assert studio.confirmed_quote("test-quote", "script", entry["inputs"], True)["used"]
        with pytest.raises(ValueError):
            studio.confirmed_quote("test-quote", "script", entry["inputs"], True)
    studio._quotes.pop("test-quote", None)
