# Lightweight frontend migration

Baseline: upstream commit `ad5496f`. Fork: https://github.com/LucasGazula/MoneyPrinterTurbo. Working branch: `migration`.

The replacement is a Svelte/TypeScript application compiled to static files and served by FastAPI. Production needs no Streamlit or Node service. This checklist defines completion; a working generation form alone is insufficient.

## Feature parity

- [ ] Script generation and rewriting, custom script and prompts, language and paragraph controls.
- [ ] Every LLM provider, endpoints, model discovery, extra provider fields and connection errors.
- [ ] LoomLoom script candidates, quote, explicit charge confirmation, polling and candidate selection.
- [ ] Stock, local, generated-video and generated-image sources with their provider settings.
- [ ] LoomLoom video capabilities, scene prompts, coverage estimate, quote and explicit charge confirmation.
- [ ] Aspect ratio, fit, duration, speed, order matching, transitions and batch variants.
- [ ] All TTS providers, voice selection, samples and complete narration preview/reuse.
- [ ] Uploaded narration, silent narration, VoxCPM reference and prompt audio and transcription.
- [ ] Random, built-in, uploaded and generated music, previews and volume controls.
- [ ] All subtitle fonts, positions, colors, outlines, backgrounds, display modes and animations.
- [ ] Background tasks, live status, logs, warnings, results, streaming and downloads.
- [ ] Disk task history, search/filter, restoration, safe deletion and local open actions.
- [ ] Preset import/export, credential backup/import and settings persistence.
- [ ] Cache statistics and bounded cleanup; version information and help/onboarding.
- [ ] Existing locales, theme, responsive layouts and keyboard accessibility.
- [ ] Social publishing settings and independent publishing status.
- [ ] Compatible existing API, CLI, launch scripts, Docker and agent workflow documentation.

## Performance and validation

- [ ] Repeatable baseline and replacement measurements: idle server RSS, startup and frontend transfer size.
- [ ] The default server imports no Streamlit, MoviePy, Whisper or provider SDKs for initial navigation.
- [ ] Form edits and navigation cause no server requests or full-page reloads.
- [ ] Heavy optional SDKs have explicit installation paths and useful missing-dependency errors.
- [ ] API and frontend behavioral tests exercise uploads, secrets, quotes, presets and restoration.
- [ ] Existing regression suite passes; frontend typecheck/build passes.
- [ ] Browser verification at desktop and mobile widths, including request and interaction checks.
- [ ] Independent finish review and design documentation.

## Migration boundary

Keep generation semantics and existing configuration formats. Expose existing services through authenticated UI endpoints; do not import the Streamlit entry point into the server. Provider credentials remain server-side and never enter generation history or public metadata. Paid execution requires confirmation of the exact quoted inputs and account. Media rendering optimization follows measured needs and preserves effects.
