# Lightweight frontend migration

Baseline: upstream commit `ad5496f`. Project: https://github.com/LucasGazula/MoneyMachine (independently maintained; originally based on MoneyPrinterTurbo). Working branch: `migration`.

The replacement is a Svelte/TypeScript application compiled to static files and served by FastAPI. Production needs no Streamlit or Node service. This checklist defines completion; a working generation form alone is insufficient.

## Feature parity

- [x] Script generation and rewriting, custom script and prompts, language and paragraph controls.
- [x] Every LLM provider, endpoints, model discovery, extra provider fields and connection errors.
- [x] LoomLoom script candidates, quote, explicit charge confirmation, polling and candidate selection.
- [x] Stock, local, generated-video and generated-image sources with their provider settings.
- [x] LoomLoom video capabilities, scene prompts, coverage estimate, quote and explicit charge confirmation.
- [x] Aspect ratio, fit, duration, speed, order matching, transitions and batch variants.
- [x] All TTS providers, voice selection, samples and complete narration preview/reuse.
- [x] Uploaded narration, silent narration, VoxCPM reference and prompt audio and transcription.
- [x] Random, built-in, uploaded and generated music, previews and volume controls.
- [x] All subtitle fonts, positions, colors, outlines, backgrounds, display modes and animations.
- [x] Background tasks, live status, logs, warnings, results, streaming and downloads.
- [x] Disk task history, search/filter, restoration, safe deletion and local open actions.
- [x] Preset import/export, credential backup/import and settings persistence.
- [x] Cache statistics and bounded cleanup; version information and help/onboarding.
- [x] Existing locales, theme, responsive layouts and keyboard accessibility.
- [x] Social publishing settings and independent publishing status.
- [x] Compatible existing API, CLI, launch scripts, Docker and agent workflow documentation.

## Performance and validation

- [x] Repeatable baseline and replacement measurements: idle server RSS, startup and frontend transfer size.
- [x] The default server imports no Streamlit, MoviePy, Whisper or provider SDKs for initial navigation.
- [x] Form edits and navigation cause no server requests or full-page reloads.
- [x] Heavy optional SDKs have explicit installation paths and useful missing-dependency errors.
- [x] API and frontend behavioral tests exercise uploads, secrets, quotes, presets and restoration.
- [x] Existing regression suite passes; frontend typecheck/build passes.
- [x] Browser verification at desktop and mobile widths, including request and interaction checks.
- [x] Independent finish review and design documentation.

## Migration boundary

Keep generation semantics and existing configuration formats. Expose existing services through authenticated UI endpoints; do not import the Streamlit entry point into the server. Provider credentials remain server-side and never enter generation history or public metadata. Paid execution requires confirmation of the exact quoted inputs and account. Media rendering optimization follows measured needs and preserves effects.

## Validation record

The checkboxes record implemented capabilities and local validation, not successful live executions on every provider or operating system. The full Python regression run passed 1,328 tests and 10,622 subtests; final studio/startup checks, including a real FFmpeg render, passed 17 tests. Additional browser checks cover provider settings, paid confirmation, narration restoration, private MiniMax IDs, exact narration-based scene coverage and authentication rotation. Typecheck/build, Ruff, shell syntax and lockfile checks pass. Combined branch coverage is approximately 81%, above the unchanged 70% gate.

Standards and Spec reviews are closed: cookie-authenticated script/term aliases, URL credential masking, active-vs-pending preview signatures, all provider settings, paid-source confirmation, historical generated script/terms, uploaded narration restoration and manual MiniMax voices were checked and corrected. The independent Impeccable finish review returned `ship`; its accessibility review influenced the control borders and mobile footer. [DESIGN.md](../DESIGN.md) and `.impeccable/design.json` document the delivered interface.

[performance.md](performance.md) records reproducible measurements and acceptance boundaries. Live paid-provider checks, actual Raspberry Pi deployment, Windows launch and Docker execution were not performed here; Docker Desktop integration is unavailable in this WSL environment. These limitations are explicit and do not imply removal of those paths. The legacy UI remains optional for comparison, rather than part of the default process.
