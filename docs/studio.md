# MoneyMachine Studio

MoneyMachine replaces the default Streamlit UI with a static Svelte/TypeScript application served by FastAPI. There is one Python server, no production Node process, and no Python reruns when editing a form or changing stages. The existing API and CLI remain available.

Local measurements and their limits are recorded in [performance.md](performance.md). The desktop/mobile UI review informed the control-border contrast and mobile action-bar layout; the design contract is in [DESIGN.md](../DESIGN.md).

## Local setup (Linux, macOS, Windows)

```sh
uv sync --frozen --no-dev
cd frontend
npm ci
npm run build
cd ..
```

Node 22.12+ is needed only to build. After building, start `sh webui.sh` or `webui.bat`, then open `http://127.0.0.1:8501`. The same process serves `/api/v1` and `/docs`; a second API server is unnecessary. Alternatively, `uv run --no-dev python main.py` serves everything on the configured API port (8080 by default).

The scripts retain `MPT_WEBUI_HOST`, `MPT_WEBUI_PORT` and automatic port fallback. For LAN access use `MPT_WEBUI_HOST=0.0.0.0`; configure `app.api_key` before exposing the service outside a trusted network. The browser login issues a bounded, expiring HttpOnly/SameSite session for native audio/video playback. Changing the server API key invalidates existing sessions. Existing API clients continue to use `x-api-key`.

On a Raspberry Pi, build the static files on your PC and copy `resource/public/studio` alongside the repository if you prefer not to install Node on the Pi. Use 64-bit Linux and a compatible Python/FFmpeg installation; this migration has not been benchmarked on Raspberry hardware. Rendering still requires resources proportional to video resolution and duration.

## Optional runtimes

All integrations and legacy formats remain in the source. Install the runtime for operations you actually use:

```sh
uv sync --frozen --no-dev --extra whisper       # uploaded narration / local transcription
uv sync --frozen --no-dev --extra azure-speech  # Azure Speech v2, where the SDK supports your platform
uv sync --frozen --no-dev --extra twelvelabs    # optional video-understanding integration
```

Pass multiple `--extra` flags together to retain multiple optional runtimes. Edge TTS, local/stock footage and the other existing provider integrations are in the default installation. Whisper models load only on explicit transcription/subtitle operations. A missing SDK or model is reported; installing Whisper does not download a model during ordinary navigation.

The former UI is retained solely as an optional rollback/reference:

```sh
uv sync --frozen --extra legacy-ui
uv run --no-sync streamlit run webui/Main.py
```

For pip installations, `requirements.txt` installs the default runtime. Install `faster-whisper==1.1.0` or `azure-cognitiveservices-speech==1.41.1` separately when needed.

## Docker

Create `config.toml` from `config.example.toml` before starting Compose.

```sh
docker compose up --build webui
```

The Dockerfile builds the frontend in a Node stage, then copies only static output into the Python image. Compose mounts configuration, storage and user media—not the repository root, which would hide the image's built UI. The default stack runs only `webui` (UI + API on 8501). `docker compose --profile api up api` optionally runs the same application on 8080. Choose one unless two independent processes are intentionally required.

Install optional Python runtimes in a derived image when required. Existing task directories, built-in songs/fonts, uploaded media, key backups and preset formats remain usable.

## Feature locations

- **Script:** custom/generated script, prompts, language and paragraphs. LoomLoom provides quoted candidate batches with explicit charge confirmation.
- **Footage:** every stock/generative source, validated local uploads, format/fit/speed/order/transitions and variants. LoomLoom resolves capabilities before quoting exact scenes.
- **Sound:** every TTS provider, sample and full narration preview, uploaded/silent narration, VoxCPM reference/prompt audio, music selection/upload/generation and mixing levels.
- **Subtitles:** fonts, placement, text/background/outline, sentence or word-by-word display and animation. The lightweight browser sample previews layout; final rendering uses the existing video engine.
- **Output/history:** task status/logs, publishing status, media attribution, native playback/range downloads, restore/delete and local open actions. Headless machines return the relative artifact location instead of opening desktop apps.
  While a video is generating, **Stop Generation** asks for confirmation before requesting cancellation. The monitor shows **Cancelling** until the worker exits, then **Cancelled**. FFmpeg renders and MoviePy frame loops stop cooperatively; an external provider request already in flight may finish or time out and may still be charged. Completed files are kept; interrupted renders are removed. Cancellation does not stop publishing a video that already finished.
- **Settings/help:** all provider and render settings, model discovery/manual models, endpoint selection, masked credentials, preset/key import/export, cache inspection/cleanup, version check and onboarding.

Voice cloning reference/prompt audio is held only in a bounded process-local cache for 30 minutes, not in task history or presets. Upload it again after expiry/restart. Restoring a task does not silently reuse private reference audio. Credential backups contain secrets by design; store them privately. Ordinary settings reads return only configured/not-configured indicators.

Paid execution is never performed as a migration test. Mocked tests verify confirmation, input/account binding and idempotency. Actual provider access depends on your credentials, account balance and service availability.

## Provider settings

Settings are grouped by function: script AI, video/images, narration, transcription/subtitles, music and social publishing. Each group shows its own provider and credentials. Switching categories keeps unsaved edits; only **Save Settings** writes them. **Advanced** retains the original technical configuration fields.

For Google-generated voice, choose **Sound → Voice Provider → Google Gemini**, then **Configure Narration AI** to enter the Gemini API key and select a TTS model. Return to Sound to choose a voice and request a sample. Gemini narration shares the Gemini script key. The default is `gemini-2.5-flash-preview-tts`; Gemini 2.5 Pro and Gemini 3.8 Flash/Flash-Lite are also available. Gemini 2.5 shows its 30 multilingual voices. Gemini 3.8 shows the extended Google voice library, filtered by the selected language and region (Brazilian Portuguese by default).

Under **Transcription & Subtitles**, choose Whisper for local speech-to-text or Gemini 3.5 Transcribe for online transcription with timed subtitles. Gemini uses the same Google API key as Google narration and Lyria music; the narration audio is uploaded to Google's Files API for transcription. Whisper is not a voice generator. **Music** separates local/uploaded tracks from Sonilo, ElevenLabs and Google Lyria AI music. ElevenLabs voice and music share one account key but have distinct model settings.

To use Google Lyria 3.5 for background music, choose **Music → Google Lyria 3.5**, enter your Gemini API key, and save. In **Sound**, select Lyria and optionally describe the music. An empty music prompt uses the video's subject and requests an instrumental track. Lyria receives text rather than the video itself, so its duration is approximate; the video mixer fits the returned MP3 to the final video. The same Gemini key can be used for scripts and narration. No music is requested when the background music volume is zero.

## Development and checks

```sh
uv sync --frozen --extra legacy-ui --extra whisper --extra azure-speech
uv run --no-sync pytest -q test
uv run --no-sync ruff check app cli.py main.py webui test docs/skill
cd frontend
npm ci
npm run check
npm run build
npx playwright install --with-deps chromium
npm test
```

`npm run dev` proxies `/api` to a local FastAPI server on 8080. Production serves the built files directly. Catalogs and settings load on first use; provider SDKs and rendering libraries are imported only for the operation that needs them. Active job polling pauses in hidden browser tabs and stops at terminal generation/publishing states.
