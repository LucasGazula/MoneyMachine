"""Authenticated browser endpoints for the static studio; no Streamlit dependency."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import shutil
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel, Field

from app.config import config
from app.controllers import base
from app.models.schema import MaterialInfo, VideoParams
from app.services import bgm, material_upload, studio, webui_task
from app.utils import file_security, utils

_sessions: dict[str, tuple[float, str]] = {}
_references: dict[str, dict] = {}
_runs: dict[str, dict] = {}


class StudioRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def checked(request):
            try:
                return await handler(request)
            except FileNotFoundError as exc:
                return JSONResponse({"detail": str(exc)}, status_code=404)
            except ValueError as exc:
                return JSONResponse({"detail": str(exc)}, status_code=400)
            except RuntimeError as exc:
                return JSONResponse({"detail": str(exc)}, status_code=409)

        return checked


def verify_browser(request: Request):
    key = config.app.get("api_key", "")
    cookie = _sessions.get(request.cookies.get("mpt_session", ""))
    if (isinstance(key, str) and cookie and cookie[0] > time.monotonic()
            and hmac.compare_digest(cookie[1], hashlib.sha256(key.encode()).hexdigest())):
        return
    base.verify_token(request)


auth_router = APIRouter(prefix="/api/v1/studio", tags=["Studio"], route_class=StudioRoute)
router = APIRouter(prefix="/api/v1/studio", tags=["Studio"],
                   dependencies=[Depends(verify_browser)], route_class=StudioRoute)


class Login(BaseModel):
    key: str = Field(default="", max_length=16000)


@auth_router.post("/session")
def login(body: Login, request: Request):
    key = config.app.get("api_key", "")
    if not isinstance(key, str) or (key and not hmac.compare_digest(body.key.encode(), key.encode())):
        raise HTTPException(401, "Invalid API key")
    token = secrets.token_urlsafe(32)
    now = time.monotonic()
    for name, (expiry, _) in list(_sessions.items()):
        if expiry <= now:
            _sessions.pop(name, None)
    if len(_sessions) >= 64:
        _sessions.pop(next(iter(_sessions)))
    _sessions[token] = (now + 28800, hashlib.sha256(key.encode()).hexdigest())
    response = JSONResponse({"authenticated": True})
    response.set_cookie("mpt_session", token, max_age=28800, httponly=True,
                        samesite="strict", secure=request.url.scheme == "https",
                        path="/api/v1/studio")
    response.headers["Cache-Control"] = "no-store"
    return response


@router.delete("/session")
def logout(request: Request):
    _sessions.pop(request.cookies.get("mpt_session", ""), None)
    response = JSONResponse({"authenticated": False})
    response.delete_cookie("mpt_session", path="/api/v1/studio")
    return response


@router.get("/bootstrap")
def bootstrap():
    return studio.bootstrap()


@router.get("/locales/{language}")
def locale(language: str):
    return studio.locale(language)


@router.get("/catalog")
def catalog():
    return studio.catalog()


@router.get("/settings")
def settings():
    response = JSONResponse(studio.settings())
    response.headers["Cache-Control"] = "no-store"
    return response


@router.patch("/settings")
def save_settings(changes: dict):
    return studio.update_settings(changes)


@router.get("/voices")
def voices(provider: str = "azure-tts-v1"):
    return {"voices": studio.voices(provider)}


@router.get("/models")
def models(provider: str):
    import requests

    spec = next((p for p in studio.LLM_PROVIDER_REGISTRY if p.provider_id == provider), None)
    if not spec:
        raise ValueError("unknown model provider")
    settings = config.snapshot_config_with_pending(config.app)
    endpoint = spec.resolve_base_url(settings.get(spec.config_key("base_url"))).rstrip("/")
    if not endpoint:
        return {"models": [spec.resolve_model_name(settings.get(spec.config_key("model_name")))]}
    key = settings.get(spec.config_key("api_key"), "")
    try:
        response = requests.get(endpoint + "/models", headers={"Authorization": f"Bearer {key}"}, timeout=15)
        response.raise_for_status()
        payload = response.json()
        return {"models": sorted(str(m["id"]) for m in payload.get("data", []) if isinstance(m, dict) and m.get("id"))}
    except (requests.RequestException, ValueError):
        raise ValueError("Cannot discover models; check the provider endpoint and credentials, or enter a model manually") from None


def _bounded_reference(identifier):
    if not identifier:
        return None
    entry = _references.get(identifier)
    if not entry or time.monotonic() - entry["created"] > 1800:
        raise ValueError("reference audio expired; upload it again")
    return entry["bytes"]


@router.post("/uploads/{kind}")
def upload(kind: str, file: UploadFile = File(...)):
    if kind == "material":
        name = material_upload.save_material_upload(file.filename or "", file.file)
    elif kind in {"music", "narration"}:
        name = bgm.save_bgm_upload(file.filename or "", file.file)
        if kind == "narration":
            source = Path(bgm.uploaded_bgm_dir()) / name
            destination = Path(utils.storage_dir("narration_uploads", create=True)) / name
            shutil.move(str(source), str(destination))
    elif kind in {"reference", "prompt"}:
        from app.services import voice

        data = file.file.read(voice.VOXCPM_REFERENCE_AUDIO_MAX_UPLOAD_BYTES + 1)
        converted = voice.prepare_voxcpm_reference_audio(data, suffix=Path(file.filename or "").suffix)
        name = str(uuid4())
        studio._remember(_references, name, {"bytes": converted})
    else:
        raise ValueError("unknown upload type")
    return {"id": name, "name": Path(file.filename or name).name, "kind": kind,
            "url": f"/api/v1/studio/uploads/{kind}/{name}" if kind not in {"reference", "prompt"} else None}


def _upload_file(kind, name):
    roots = {"material": material_upload.uploaded_material_dir(), "music": bgm.uploaded_bgm_dir(),
             "narration": utils.storage_dir("narration_uploads", create=True)}
    if kind not in roots or Path(name).name != name or "\\" in name:
        raise ValueError("invalid upload identifier")
    return file_security.resolve_path_within_directory(roots[kind], name)


@router.get("/uploads/{kind}/{name}")
def uploaded_file(kind: str, name: str):
    return FileResponse(_upload_file(kind, name))


@router.get("/music/{name}")
def music(name: str):
    return FileResponse(bgm.resolve_bgm_file(name))


@router.post("/transcription")
def transcription(body: dict):
    from app.services import subtitle

    audio = _bounded_reference(body.get("id"))
    if not audio:
        raise ValueError("upload prompt audio first")
    if subtitle.WhisperModel is None:
        raise ValueError("Install transcription support with: uv sync --extra whisper")
    return {"text": subtitle.transcribe_audio_bytes(audio)}


class Generation(BaseModel):
    params: VideoParams
    narration_id: str = ""
    reference_id: str = ""
    prompt_id: str = ""
    prompt_text: str = Field(default="", max_length=16000)
    preview_id: str = ""
    quote_id: str = ""
    quote_inputs: dict = Field(default_factory=dict)
    charge_confirmed: bool = False


def validate_params(params):
    for name, low, high in (("video_count", 1, 100), ("video_clip_speed", .5, 2),
                            ("voice_rate", .25, 4), ("voice_volume", 0, 10),
                            ("bgm_volume", 0, 10), ("font_size", 1, 500),
                            ("stroke_width", 0, 50), ("n_threads", 1, 64),
                            ("custom_position", 0, 100), ("video_clip_duration", 1, 600)):
        value = getattr(params, name)
        if value is None or not low <= value <= high:
            raise ValueError(f"{name} must be between {low} and {high}")
    if len(params.video_script) > 100000 or len(params.video_subject) > 16000:
        raise ValueError("script or subject is too long")
    if params.video_source not in studio.SOURCES:
        raise ValueError("unknown material source")
    if not params.video_subject.strip() and not params.video_script.strip():
        raise ValueError("provide a subject or a script")
    if params.subtitle_enabled:
        file_security.resolve_path_within_directory(utils.font_dir(), params.font_name or "")
    if params.bgm_type in {"custom", "preset"}:
        resolver = bgm.resolve_builtin_bgm_file if params.bgm_type == "preset" else bgm.resolve_bgm_file
        params.bgm_file = resolver(params.bgm_file)
    if params.video_source == "local":
        if not params.video_materials:
            raise ValueError("upload at least one local video or image")
        params.video_materials = [MaterialInfo(provider="local", url=_upload_file("material", m.url))
                                  for m in params.video_materials]
    elif params.video_materials:
        raise ValueError("uploaded materials can only be used with the local source")
    if params.custom_audio_file:
        raise ValueError("use a narration upload, not a server file path")
    return params


@router.post("/generate", status_code=202)
def generate(body: Generation):
    params = validate_params(body.params.model_copy(deep=True))
    reference = _bounded_reference(body.reference_id)
    prompt = _bounded_reference(body.prompt_id)
    narration = _upload_file("narration", body.narration_id) if body.narration_id else None
    confirmed = None
    if params.video_source == "loomloom":
        if (body.quote_inputs.get("subject") != params.video_subject
                or body.quote_inputs.get("aspect_ratio") != params.video_aspect):
            raise ValueError("video parameters changed; request a new quote")
        confirmed = studio.confirmed_video(body.quote_id, body.quote_inputs, body.charge_confirmed)
    task_id = str(uuid4())
    preview = studio.reusable_preview(body.preview_id, params, task_id, reference, prompt, body.prompt_text)
    if narration:
        folder = Path(utils.task_dir(task_id))
        destination = folder / ("uploaded-audio" + Path(narration).suffix)
        shutil.copyfile(narration, destination)
        params.custom_audio_file = str(destination)
    webui_task.submit_generation(task_id, params,
        capture_logs=not config.ui.get("hide_log", False), voice_preview=preview,
        loomloom_video_request=confirmed, voxcpm_reference_audio=reference,
        voxcpm_prompt_audio=prompt, voxcpm_prompt_text=body.prompt_text)
    return {"task_id": task_id}


class Preview(Generation):
    text: str = Field(min_length=1, max_length=16000)
    full: bool = False


@router.post("/previews")
def preview(body: Preview):
    if body.params.voice_name and "V2" in body.params.voice_name:
        from importlib.util import find_spec

        try:
            available = find_spec("azure.cognitiveservices.speech") is not None
        except ModuleNotFoundError:
            available = False
        if not available:
            raise ValueError("Install Azure Speech support with: uv sync --extra azure-speech")
    return studio.preview(body.params, text=body.text, full=body.full,
        reference_audio=_bounded_reference(body.reference_id),
        prompt_audio=_bounded_reference(body.prompt_id), prompt_text=body.prompt_text)


@router.get("/previews/{identifier}")
def preview_file(identifier: str):
    return FileResponse(studio.get_preview(identifier)["file"], media_type="audio/mpeg")


@router.get("/tasks")
def tasks(limit: int = Query(30, ge=1, le=1000)):
    return {"tasks": studio.history(limit)}


@router.get("/tasks/{task_id}")
def task_detail(task_id: str, logs: bool = False):
    detail = studio.task_detail(task_id)
    if logs:
        detail["logs"] = webui_task.get_task_logs(task_id)
    return detail


@router.delete("/tasks/{task_id}")
def delete_task(task_id: str):
    studio.delete_task(task_id)
    return {"deleted": True}


@router.get("/tasks/{task_id}/files/{filename}")
def task_file(task_id: str, filename: str, download: bool = False):
    if Path(filename).name != filename or "\\" in filename:
        raise ValueError("invalid filename")
    path = file_security.resolve_path_within_directory(str(studio.task_path(task_id)), filename)
    return FileResponse(path, filename=filename if download else None)


@router.post("/tasks/{task_id}/open")
def open_task(task_id: str, body: dict):
    target = studio.task_path(task_id)
    if not target.is_dir():
        raise FileNotFoundError("task not found")
    if body.get("file"):
        target = Path(file_security.resolve_path_within_directory(str(target), body["file"]))
        if target.suffix.lower() != ".mp4":
            raise ValueError("only video artifacts can be opened")
    relative = os.path.relpath(target, utils.root_dir())
    if os.getenv("HEADLESS", "").lower() in {"1", "true"} or (sys.platform.startswith("linux") and not os.getenv("DISPLAY")):
        return {"opened": False, "path": relative}
    if sys.platform.startswith("win"):
        os.startfile(str(target))
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(target)])
    return {"opened": True, "path": relative}


@router.post("/presets/export")
def export_preset(params: VideoParams):
    return studio.preset(params.model_dump(mode="json"))


@router.post("/presets/import")
def import_preset(body: dict):
    if body.get("schema") != "moneyprinterturbo.settings-preset" or body.get("version") != 1:
        raise ValueError("unsupported preset format")
    return {"params": studio.preset(body.get("params", {}), importing=True)}


@router.get("/keys/export")
def export_keys():
    response = JSONResponse(studio.key_backup())
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Disposition"] = 'attachment; filename="moneyprinterturbo-keys.json"'
    return response


@router.post("/keys/import")
def import_keys(body: dict):
    if body.get("schema") != "moneyprinterturbo.key-backup" or body.get("version") != 1:
        raise ValueError("unsupported key backup")
    if not isinstance(body.get("keys"), dict):
        raise ValueError("key backup must contain named sections")
    current = studio.settings()["sections"]
    changes = {name: {key: value for key, value in values.items() if value and key in current[name]}
               for name, values in body.get("keys", {}).items()
               if name in current and name != "ui" and isinstance(values, dict)}
    return studio.update_settings(changes)


@router.get("/cache")
def cache_stats(days: int | None = Query(None, ge=1)):
    from app.services import cache_manager

    return asdict(cache_manager.get_video_cache_stats(max_age_days=days))


@router.delete("/cache")
def clean_cache(days: int | None = Query(None, ge=1)):
    from app.services import cache_manager

    return asdict(cache_manager.clean_video_cache(max_age_days=days))


@router.get("/version")
def version():
    from app.services import version_checker

    return {"version": studio.__version__, "update": version_checker.get_available_update(studio.__version__)}


@router.get("/loomloom/capabilities")
def capabilities():
    from app.services import loomloom

    values = config.snapshot_config_with_pending(config.app)
    return asdict(loomloom.LoomLoomVideoBackend(loomloom.video_settings_from_mapping(values)).resolve_video_capability())


class QuoteRequest(BaseModel):
    kind: str
    inputs: dict
    quote_id: str = ""
    confirmed: bool = False


@router.post("/loomloom/quote")
def quote(body: QuoteRequest):
    return studio.quote_loomloom(body.kind, body.inputs)


@router.post("/loomloom/scripts", status_code=202)
def execute_script(body: QuoteRequest):
    entry = studio.confirmed_quote(body.quote_id, "script", body.inputs, body.confirmed)
    try:
        run = entry["backend"].execute(entry["batch"], client_request_id=entry["client_request_id"],
                                       listing_version_id=entry["quote"].listing_version_id, confirm=True)
    except Exception:
        # Keep the same idempotency key if the response was lost; never create another charge.
        entry["used"] = False
        raise
    studio._remember(_runs, run.run_id, {"backend": entry["backend"]})
    return asdict(run)


@router.get("/loomloom/scripts/{run_id}")
def script_run(run_id: str):
    entry = _runs.get(run_id)
    if not entry:
        raise FileNotFoundError("run not found in this server session")
    backend = entry["backend"]
    result = asdict(backend.get_run(run_id))
    if result["status"] in {"completed", "failed", "cancelled"}:
        result["results"] = asdict(backend.get_script_results(run_id))
    return result
