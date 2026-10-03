import subprocess
import sys
import threading
from unittest.mock import patch
from types import SimpleNamespace

import pytest

from app.services import cancellation


def test_running_render_process_is_reaped_and_other_tasks_are_untouched():
    started = threading.Event()
    processes = []
    outcome = []
    popen = subprocess.Popen

    def launch(*args, **kwargs):
        process = popen(*args, **kwargs)
        processes.append(process)
        started.set()
        return process

    def render():
        try:
            with cancellation.scope("render-to-stop"):
                cancellation.run([sys.executable, "-c", "import time; time.sleep(60)"], capture_output=True)
        except cancellation.TaskCancelled:
            outcome.append("cancelled")

    with patch.object(cancellation.subprocess, "Popen", side_effect=launch):
        worker = threading.Thread(target=render)
        worker.start()
        try:
            assert started.wait(3)
            assert cancellation.request("render-to-stop")
            worker.join(3)
            assert not worker.is_alive()
            assert outcome == ["cancelled"]
            assert processes[0].poll() is not None
            with cancellation.scope("another-task"):
                cancellation.check()
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
            worker.join(3)
    assert not cancellation.request("render-to-stop")


def test_queued_cancellation_skips_work_and_moviepy_observes_cancellation():
    cancellation.prepare("queued")
    cancellation.request("queued")
    with pytest.raises(cancellation.TaskCancelled), cancellation.scope("queued"):
        pytest.fail("a cancelled queued task must not start")
    with cancellation.scope("moviepy"):
        logger = cancellation.moviepy_logger()
        cancellation.request("moviepy")
        with pytest.raises(cancellation.TaskCancelled):
            logger.bars_callback("frame", "index", 1)


def test_narration_does_not_retry_provider_after_cancellation(tmp_path):
    from app.services import voice

    def failed_request(*args, **kwargs):
        cancellation.request("narration")
        return SimpleNamespace(status_code=503, text="temporary failure")

    with (
        cancellation.scope("narration"),
        patch.object(voice.config, "minimax_tts", {}),
        patch.object(voice, "get_minimax_tts_api_key", return_value="test-key"),
        patch.object(voice, "get_minimax_tts_endpoint", return_value="https://example.invalid/tts"),
        patch.object(voice.requests, "post", side_effect=failed_request) as request,
    ):
        with pytest.raises(cancellation.TaskCancelled):
            voice.minimax_tts("Test narration", "test-voice", 1, str(tmp_path / "audio.mp3"))
        request.assert_called_once()


@pytest.mark.parametrize("engine", ["ffmpeg", "moviepy"])
def test_real_render_cancellation_removes_partial_output(tmp_path, engine):
    from moviepy import ColorClip
    from app.services import video

    started = threading.Event()
    resume = threading.Event()
    output = tmp_path / "final-1.mp4"
    outcome = []
    processes = []
    popen = subprocess.Popen

    def launch(*args, **kwargs):
        process = popen(*args, **kwargs)
        processes.append(process)
        if engine == "ffmpeg":
            started.set()
        return process

    def frame(get_frame, t):
        if t > 0:
            started.set()
            assert resume.wait(3)
        return get_frame(t)

    def render():
        try:
            with cancellation.scope(engine):
                if engine == "ffmpeg":
                    video._run_concat_with_heartbeat([
                        video.get_ffmpeg_binary(), "-y", "-re", "-f", "lavfi",
                        "-i", "color=black:s=64x64:r=10", "-t", "60",
                        "-c:v", "libx264", str(output),
                    ], str(output))
                else:
                    with ColorClip((64, 64), color=(0, 0, 0)).with_duration(60) as clip:
                        video._write_videofile_with_codec_fallback(
                            clip.transform(frame), str(output), "libx264", fps=10,
                        )
        except cancellation.TaskCancelled:
            outcome.append("cancelled")

    with patch.object(cancellation.subprocess, "Popen", side_effect=launch):
        worker = threading.Thread(target=render)
        worker.start()
        try:
            assert started.wait(3)
            assert cancellation.request(engine)
            resume.set()
            worker.join(5)
            assert not worker.is_alive()
            assert outcome == ["cancelled"]
            assert not output.exists()
            assert processes and all(process.poll() is not None for process in processes)
        finally:
            resume.set()
            for process in processes:
                if process.poll() is None:
                    process.kill()
            worker.join(3)
