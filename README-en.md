# MoneyMachine

A short-video studio with scripts, footage, narration, subtitles, music, and generation history. Svelte/TypeScript assets are served by FastAPI; the REST API and CLI remain available.

[Português brasileiro](README.md) · [Studio guide](docs/studio.md) · [Issues](https://github.com/LucasGazula/MoneyMachine/issues)

## Setup

Requires Python 3.11+, uv, FFmpeg, and Node 22.12+ to build the frontend.

```sh
git clone https://github.com/LucasGazula/MoneyMachine.git
cd MoneyMachine
cp config.example.toml config.toml
uv sync --frozen --no-dev
cd frontend
npm ci
npm run build
cd ..
sh webui.sh
```

Open http://127.0.0.1:8501 and configure providers in Settings. On Windows, copy the configuration file and use `webui.bat`. Credentials stay in the local, Git-ignored `config.toml`.

For local transcription, install the Whisper extra with `uv sync --frozen --no-dev --extra whisper`. See the [studio guide](docs/studio.md) for optional runtimes, provider settings, API access, CLI use, and development checks.

## Docker

Create `config.toml`, then run:

```sh
docker compose up --build webui
```

This builds MoneyMachine from this repository. `docker-compose.release.yml` uses `ghcr.io/lucasgazula/moneymachine:latest` once our own image is published.

## Features

The studio includes provider settings grouped by purpose, Gemini narration/transcription, Google Lyria music, FFmpeg rendering optimizations with MoviePy fallback, cooperative cancellation, and completed-video playback. See [migration notes](docs/frontend-migration.md) for implementation details.

## Origin and license

MoneyMachine is maintained independently by [LucasGazula](https://github.com/LucasGazula). It originated from Harry's [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) and no longer follows its updates. Original Git history and attribution are retained under the [MIT license](LICENSE).
