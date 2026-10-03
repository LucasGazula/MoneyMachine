"""Browser-facing operations without importing a UI or media runtime at startup."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
import shutil
import threading
import time
from dataclasses import asdict
from functools import lru_cache
from pathlib import Path
from uuid import uuid4
from urllib.parse import parse_qs, urlsplit

import toml

from app import __version__
from app.config import config
from app.models import const
from app.models.llm_provider import LLM_PROVIDER_REGISTRY
from app.models.schema import VideoParams
from app.services import bgm, cancellation, state, task
from app.utils import file_security, utils


SOURCES = [
    "pexels",
    "pixabay",
    "coverr",
    "local",
    "openai_image",
    "wavespeed",
    "volcengine_seedance",
    "ofox",
    "metaso_minimax",
    "muapi",
    "loomloom",
]
TTS_PROVIDERS = {
    "azure-tts-v1": "Edge TTS",
    "azure-tts-v2": "Azure Speech",
    "siliconflow": "SiliconFlow",
    "gemini-tts": "Google Gemini",
    "mimo-tts": "Xiaomi MiMo",
    "minimax-tts": "MiniMax",
    "elevenlabs": "ElevenLabs",
    "chatterbox": "Chatterbox",
    "kokoro": "Kokoro",
    "fish_audio": "Fish Audio",
    "voxcpm": "VoxCPM",
}
SECRET_SUFFIXES = (
    "api_key",
    "api_keys",
    "api_token",
    "access_key",
    "secret_key",
    "speech_key",
    "password",
)
PRESET_EXCLUDED = {"video_materials", "custom_audio_file", "bgm_file"}
_quotes: dict[str, dict] = {}
_previews: dict[str, dict] = {}
_session_lock = threading.RLock()
_SESSION_TTL = 1800
_MAX_SESSIONS = 16


@lru_cache(maxsize=1)
def config_defaults():
    return toml.load(Path(utils.root_dir()) / "config.example.toml")


def config_sections():
    return {
        name: getattr(config, name)
        for name in config_defaults()
        if isinstance(getattr(config, name, None), dict)
    }


def is_secret(key):
    return key.endswith(SECRET_SUFFIXES)


def is_private_setting(section, key, value):
    if is_secret(key) or (section == "proxy" and key in {"http", "https"}):
        return True
    if isinstance(value, str) and "://" in value:
        try:
            parsed = urlsplit(value)
            return bool(
                parsed.username
                or parsed.password
                or any(
                    is_secret(name)
                    or name.lower() in {"token", "key", "signature", "sig"}
                    for name in parse_qs(parsed.query)
                )
            )
        except ValueError:
            return True
    return False


def settings():
    sections = {}
    configured = {}
    for name, section in config_sections().items():
        values = {
            **config_defaults().get(name, {}),
            **config.snapshot_config_with_pending(section),
        }
        configured[name] = {
            key: bool(value)
            for key, value in values.items()
            if is_private_setting(name, key, value)
        }
        sections[name] = {
            key: ([] if isinstance(value, list) else "")
            if is_private_setting(name, key, value)
            else value
            for key, value in values.items()
        }
    return {"sections": sections, "configured": configured}


def update_settings(changes):
    if not isinstance(changes, dict):
        raise ValueError("settings must contain named sections")
    sections = config_sections()
    validated = []
    for name, entries in changes.items():
        if name not in sections or not isinstance(entries, dict):
            raise ValueError(f"unknown configuration section: {name}")
        allowed = {**config_defaults().get(name, {}), **dict(sections[name])}
        if name == "app":
            for provider in LLM_PROVIDER_REGISTRY:
                allowed.update(
                    {
                        provider.config_key("api_key"): "",
                        provider.config_key("base_url"): "",
                        provider.config_key("model_name"): "",
                    }
                )
                allowed.update(
                    {
                        provider.config_key(field.config_suffix): ""
                        for field in provider.extra_fields
                    }
                )
        if name == "ui":
            allowed.update(VideoParams(video_subject="").model_dump(mode="json"))
            allowed.update(
                language="pt",
                theme="light",
                tts_server="azure-tts-v1",
                voice_mode="tts",
                gemini_voice_locale="pt-BR",
                loomloom_candidate_count=3,
                loomloom_script_duration_seconds=60,
            )
        for key, value in entries.items():
            if key not in allowed:
                raise ValueError(f"unknown configuration field: {name}.{key}")
            if name == "ui" and key in VideoParams.model_fields:
                if key in PRESET_EXCLUDED:
                    raise ValueError("uploaded resources cannot be stored as defaults")
                VideoParams.model_validate(
                    {**VideoParams(video_subject="").model_dump(), key: value}
                )
                validated.append((sections[name], key, value))
                continue
            expected = allowed[key]
            if isinstance(expected, bool):
                valid = isinstance(value, bool)
            elif isinstance(expected, (int, float)):
                valid = (
                    isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and math.isfinite(value)
                )
            elif isinstance(expected, list):
                valid = isinstance(value, list) and all(
                    isinstance(v, str) for v in value
                )
            else:
                valid = isinstance(value, str) and len(value) <= 16000
            if not valid:
                raise ValueError(f"invalid value for {name}.{key}")
            validated.append((sections[name], key, value))
    for section, key, value in validated:
        config.update_config_nonblocking(section, key, value)
    saved = config.try_save_config()
    return {"saved": saved, "pending": not saved}


def defaults():
    params = VideoParams(video_subject="").model_dump(mode="json")
    ui = config.snapshot_config_with_pending(config.ui)
    for key in params:
        if key in ui and key not in PRESET_EXCLUDED:
            params[key] = ui[key]
    params["video_source"] = ui.get(
        "video_source", config.app.get("video_source", "pexels")
    )
    params["voice_name"] = params.get("voice_name") or "pt-BR-FranciscaNeural-Female"
    # Old preferences may contain obsolete values; don't make the page unusable.
    try:
        return VideoParams.model_validate(params).model_dump(mode="json")
    except ValueError:
        return VideoParams(video_subject="").model_dump(mode="json")


def bootstrap():
    locale_dir = Path(utils.root_dir()) / "webui" / "i18n"
    return {
        "version": __version__,
        "defaults": defaults(),
        "schema": VideoParams.model_json_schema(),
        "llm_providers": [asdict(provider) for provider in LLM_PROVIDER_REGISTRY],
        "sources": SOURCES,
        "tts_providers": TTS_PROVIDERS,
        "locales": sorted(path.stem for path in locale_dir.glob("*.json")),
        "ui": {
            key: value for key, value in dict(config.ui).items() if not is_secret(key)
        },
        "llm_provider": config.app.get("llm_provider", "moonshot"),
        "script_backend": config.app.get("script_generation_backend", "local"),
    }


@lru_cache(maxsize=20)
def locale(language):
    if language not in bootstrap()["locales"]:
        raise ValueError("unknown language")
    with (
        Path(utils.root_dir()) / "webui" / "i18n" / f"{language}.json"
    ).open() as source:
        return json.load(source)


def catalog():
    return {
        "fonts": sorted(
            path.name
            for path in Path(utils.font_dir()).iterdir()
            if path.suffix.lower() in {".ttf", ".ttc", ".otf"}
        ),
        "music": [
            {"name": Path(path).name, "id": Path(path).name}
            for path in bgm.list_bgm_files()
        ],
        "builtin_music": [Path(path).name for path in bgm.list_builtin_bgm_files()],
    }


def voices(provider):
    if provider not in TTS_PROVIDERS:
        raise ValueError("unknown speech provider")
    from app.services import voice

    if provider in {"azure-tts-v1", "azure-tts-v2"}:
        result = [
            v
            for v in voice.get_all_azure_voices()
            if ("V2" in v) == (provider == "azure-tts-v2")
        ]
    elif provider == "elevenlabs":
        result = voice.get_elevenlabs_voices(config.elevenlabs.get("api_key", ""))
    elif provider == "minimax-tts":
        result = voice.get_minimax_voices(config.minimax_tts.get("voice_id"))
        try:
            entries = voice.get_minimax_voice_catalog()
            result += [f"minimax:{entry['voice_id']}" for entry in entries]
        except (ValueError, RuntimeError):
            # A private/cloned ID remains usable even if catalog discovery fails.
            pass
        result = list(dict.fromkeys(result))
    else:
        getter = {
            "siliconflow": voice.get_siliconflow_voices,
            "gemini-tts": voice.get_gemini_voices,
            "mimo-tts": voice.get_mimo_voices,
            "chatterbox": voice.get_chatterbox_voices,
            "kokoro": voice.get_kokoro_voices,
            "fish_audio": voice.get_fish_audio_voices,
            "voxcpm": voice.get_voxcpm_voices,
        }[provider]
        result = getter()
    return result


def task_path(task_id):
    if not isinstance(task_id, str) or not re.fullmatch(
        r"[A-Za-z0-9_-]{1,128}", task_id
    ):
        raise ValueError("invalid task identifier") from None
    root = utils.task_dir()
    candidate = Path(root) / task_id
    if candidate.is_symlink():
        raise ValueError("task symlinks are not allowed")
    return Path(
        file_security.resolve_path_within_directory(root, task_id, require_file=False)
    )


def artifact_url(task_id, filename):
    return f"/api/v1/studio/tasks/{task_id}/files/{filename}"


def task_detail(task_id):
    folder = task_path(task_id)
    live = state.state.get_task(task_id) or {}
    payload = {}
    try:
        payload = json.loads((folder / "script.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    if not isinstance(payload, dict):
        payload = {}
    params = payload.get("params")
    if not isinstance(params, dict):
        params = {}
    params = dict(params)
    if isinstance(payload.get("script"), str):
        params["video_script"] = payload["script"]
    if isinstance(payload.get("search_terms"), (str, list)):
        params["video_terms"] = payload["search_terms"]
    files = []
    if folder.is_dir():
        files = [
            {
                "name": file.name,
                "url": artifact_url(task_id, file.name),
                "size": file.stat().st_size,
            }
            for file in folder.iterdir()
            if file.is_file()
            and not file.is_symlink()
            and not file.name.startswith(".")
        ]
    if not live and not files:
        raise FileNotFoundError("task not found")
    videos = [
        entry
        for entry in files
        if entry["name"].startswith("final-") and entry["name"].endswith(".mp4")
        and live.get("state") != const.TASK_STATE_PROCESSING
    ]
    result = {
        "task_id": task_id,
        "state": const.TASK_STATE_COMPLETE if videos else None,
        "progress": 100 if videos else 0,
        **live,
        "cancel_requested": cancellation.requested(task_id),
        "params": params,
        "files": files,
        "video_files": videos,
        "material_sources": payload.get("material_sources", []),
        "subject": params.get("video_subject") or live.get("video_subject") or task_id,
        "mtime": folder.stat().st_mtime if folder.exists() else 0,
    }
    result.pop("cross_post_owner", None)
    return result


def history(limit=30):
    entries = []
    with os.scandir(utils.task_dir()) as folders:
        for entry in folders:
            if not entry.is_dir(follow_symlinks=False):
                continue
            try:
                task_path(entry.name)
                entries.append((entry.stat(follow_symlinks=False).st_mtime, entry.name))
            except (ValueError, OSError):
                continue
    live, _ = state.state.get_all_tasks(1, 100)
    entries.extend(
        (time.time(), t["task_id"])
        for t in live
        if t.get("state") == const.TASK_STATE_PROCESSING
    )
    result = []
    seen = set()
    for _, task_id in sorted(entries, reverse=True):
        if task_id in seen:
            continue
        seen.add(task_id)
        try:
            detail = task_detail(task_id)
        except (FileNotFoundError, ValueError, OSError):
            continue
        result.append(
            {
                key: detail.get(key)
                for key in (
                    "task_id",
                    "subject",
                    "state",
                    "progress",
                    "mtime",
                    "cross_post_state",
                    "video_files",
                    "error",
                )
            }
        )
        if len(result) >= limit:
            break
    return result


def delete_task(task_id):
    folder = task_path(task_id)
    live = state.state.get_task(task_id)
    if task.is_task_busy(live):
        raise RuntimeError("task is still generating or publishing")
    if not folder.exists() and live is None:
        raise FileNotFoundError("task not found")
    if folder.exists():
        shutil.rmtree(folder)
    state.state.delete_task(task_id)


def preset(params, *, importing=False):
    clean = {key: value for key, value in params.items() if key not in PRESET_EXCLUDED}
    if params.get("bgm_type") == "preset" and params.get("bgm_file"):
        clean["bgm_file"] = Path(bgm.resolve_builtin_bgm_file(params["bgm_file"])).name
    clean.setdefault("video_subject", "")
    validated = VideoParams.model_validate(clean).model_dump(mode="json")
    if importing:
        return validated
    return {
        "schema": "moneyprinterturbo.settings-preset",
        "version": 1,
        "app_version": __version__,
        "params": {
            key: value
            for key, value in validated.items()
            if key not in PRESET_EXCLUDED or key in clean
        },
    }


def key_backup():
    companions = {"azure": {"speech_region"}, "app": {"upload_post_username"}}
    companions["app"].update(
        provider.config_key(field.config_suffix)
        for provider in LLM_PROVIDER_REGISTRY
        for field in provider.extra_fields
    )
    return {
        "schema": "moneyprinterturbo.key-backup",
        "version": 1,
        "app_version": __version__,
        "keys": {
            name: {
                key: value
                for key, value in config.snapshot_config_with_pending(section).items()
                if value
                and (
                    is_private_setting(name, key, value)
                    or key in companions.get(name, set())
                )
            }
            for name, section in config_sections().items()
            if name != "ui"
        },
    }


def _remember(cache, key, entry):
    with _session_lock:
        expired = [
            name
            for name, data in cache.items()
            if time.monotonic() - data["created"] > _SESSION_TTL
        ]
        if len(cache) >= _MAX_SESSIONS:
            expired.append(next(iter(cache)))
        for name in expired:
            removed = cache.pop(name, {})
            file = removed.get("file")
            if file:
                Path(file).unlink(missing_ok=True)
        cache[key] = {**entry, "created": time.monotonic()}


def preview(
    params, *, text, full=False, reference_audio=None, prompt_audio=None, prompt_text=""
):
    from app.services import voice

    text = text.strip()
    if not text or len(text) > 16000:
        raise ValueError("preview text must contain between 1 and 16000 characters")
    identifier = str(uuid4())
    output = Path(utils.storage_dir("previews", create=True)) / f"{identifier}.mp3"
    try:
        with config.try_runtime_config_lock() as acquired:
            if not acquired:
                raise RuntimeError(
                    "generation is using the speech configuration; try again shortly"
                )
            active_settings = {
                name: dict(section)
                for name, section in config_sections().items()
                if name != "ui"
            }
            signature = hashlib.sha256(
                json.dumps(active_settings, sort_keys=True).encode()
            ).hexdigest()
            kwargs = {
                "text": text,
                "voice_name": voice.parse_voice_name(params.voice_name),
                "voice_rate": params.voice_rate,
                "voice_volume": params.voice_volume,
                "voice_file": str(output),
            }
            if reference_audio:
                kwargs["voxcpm_reference_audio"] = reference_audio
            if prompt_audio:
                kwargs.update(
                    voxcpm_prompt_audio=prompt_audio, voxcpm_prompt_text=prompt_text
                )
            maker = voice.tts(**kwargs)
        if maker is None or not output.is_file() or not output.stat().st_size:
            raise ValueError(
                "speech preview failed; check the selected voice and provider settings"
            )
        duration = voice.get_audio_duration(str(output))
        _remember(
            _previews,
            identifier,
            {
                "file": str(output),
                "sub_maker": maker,
                "duration": duration,
                "full": full,
                "text": text,
                "params": params.model_dump(mode="json"),
                "signature": signature,
                "reference_signature": reference_signature(
                    reference_audio, prompt_audio, prompt_text
                ),
            },
        )
        return {
            "id": identifier,
            "duration": duration,
            "url": f"/api/v1/studio/previews/{identifier}",
            "full": full,
        }
    except Exception:
        output.unlink(missing_ok=True)
        raise


def settings_signature():
    # Hash only in memory; neither the digest nor credentials enter history/logs.
    return {
        name: config.snapshot_config_with_pending(section)
        for name, section in config_sections().items()
        if name != "ui"
    }


def get_preview(identifier):
    with _session_lock:
        entry = _previews.get(identifier)
        if not entry or time.monotonic() - entry["created"] > _SESSION_TTL:
            raise FileNotFoundError("preview expired; generate it again")
        return entry


def reference_signature(reference_audio, prompt_audio, prompt_text):
    digest = hashlib.sha256()
    for value in (reference_audio or b"", prompt_audio or b"", prompt_text.encode()):
        digest.update(len(value).to_bytes(8, "big"))
        digest.update(value)
    return digest.hexdigest()


def reusable_preview(
    identifier, params, task_id, reference_audio=None, prompt_audio=None, prompt_text=""
):
    if not identifier or params.voice_volume != 1:
        return None
    try:
        entry = get_preview(identifier)
    except FileNotFoundError:
        return None
    signature = hashlib.sha256(
        json.dumps(settings_signature(), sort_keys=True).encode()
    ).hexdigest()
    if (
        not entry["full"]
        or entry["text"] != params.video_script.strip()
        or entry["signature"] != signature
        or not entry["sub_maker"]
        or entry.get("reference_signature")
        != reference_signature(reference_audio, prompt_audio, prompt_text)
        or any(
            entry["params"][key] != getattr(params, key)
            for key in ("voice_name", "voice_rate", "voice_volume")
        )
    ):
        return None
    target = Path(utils.task_dir(task_id)) / "preview-audio.mp3"
    shutil.copyfile(entry["file"], target)
    return {
        "audio_file": str(target),
        "duration": entry["duration"],
        "sub_maker": entry["sub_maker"],
        "script": params.video_script.strip(),
        "voice_name": params.voice_name,
        "voice_rate": params.voice_rate,
        "voice_volume": params.voice_volume,
    }


def quote_loomloom(kind, inputs):
    from app.services import loomloom

    values = config.snapshot_config_with_pending(config.app)
    if kind == "script":
        backend = loomloom.LoomLoomScriptBackend(
            loomloom.LoomLoomSettings.from_mapping(values)
        )
        batch = backend.prepare_script_batch(**inputs)
    elif kind == "video":
        backend = loomloom.LoomLoomVideoBackend(
            loomloom.video_settings_from_mapping(values)
        )
        capability = backend.resolve_video_capability()
        if inputs["model_id"] not in {model.model_id for model in capability.models}:
            raise ValueError("selected model is no longer available")
        if inputs["aspect_ratio"] not in capability.aspect_ratios:
            raise ValueError("selected aspect ratio is unavailable")
        batch = backend.prepare_video_batch(**inputs)
    else:
        raise ValueError("unknown quote type")
    quote = backend.quote(batch)
    identifier = str(uuid4())
    _remember(
        _quotes,
        identifier,
        {
            "kind": kind,
            "backend": backend,
            "batch": batch,
            "quote": quote,
            "inputs": copy.deepcopy(inputs),
            "used": False,
            "client_request_id": f"mpt-{kind}-{identifier}",
        },
    )
    return {
        "id": identifier,
        **{key: value for key, value in asdict(quote).items() if key != "input_rows"},
    }


def confirmed_quote(identifier, kind, inputs, confirmed):
    from app.services import loomloom

    if confirmed is not True:
        raise ValueError("explicit charge confirmation is required")
    with _session_lock:
        entry = _quotes.get(identifier)
        if (
            not entry
            or entry["kind"] != kind
            or entry["used"]
            or time.monotonic() - entry["created"] > _SESSION_TTL
            or entry["inputs"] != inputs
        ):
            raise ValueError("quote expired or inputs changed; request a new quote")
        current = config.snapshot_config_with_pending(config.app)
        original = entry["backend"].settings
        if loomloom.resolve_api_token(current) != original.api_token or str(
            current.get("loomloom_base_url") or loomloom.DEFAULT_BASE_URL
        ).rstrip("/") != original.base_url.rstrip("/"):
            raise ValueError("account changed; request a new quote")
        entry["used"] = True
        return entry


def confirmed_video(identifier, inputs, confirmed):
    from app.services import loomloom

    entry = confirmed_quote(identifier, "video", inputs, confirmed)
    return loomloom.LoomLoomConfirmedVideoRequest(
        settings=entry["backend"].settings,
        batch=entry["batch"],
        listing_version_id=entry["quote"].listing_version_id,
        client_request_id=entry["client_request_id"],
    )
