"""Keep first-page requests independent of video/model runtimes."""

import json
import subprocess
import sys


def test_api_import_does_not_load_media_or_model_libraries():
    script = """
import json
import sys
import app.asgi
print(json.dumps([name for name in
    ('streamlit', 'moviepy', 'faster_whisper', 'numpy', 'openai', 'litellm')
    if name in sys.modules]))
"""
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=True
    )
    assert json.loads(result.stdout.splitlines()[-1]) == []
