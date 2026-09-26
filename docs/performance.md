# Lightweight studio measurements

Measured on 2026-09-26 in this Linux/WSL workspace, not on a Raspberry Pi. Baseline is upstream commit `ad5496f`, extracted with `git archive` into an isolated temporary directory. Both versions used the same Python 3.11 environment; the browser was Chromium 153.0.8010.12 via Playwright. No video generation, provider calls or Whisper models were involved in the idle comparison.

| Measurement | Original Streamlit | Static Svelte + FastAPI |
| --- | ---: | ---: |
| Server RSS after opening the editor, without rendering | 231–235 MiB | 66–67 MiB |
| Editor ready, median of three fresh browser contexts | 2,574 ms | 163 ms |
| Initial HTTP transfer to editor-ready, same browser runs | 3,648,142 bytes | 100,397 bytes |
| Warm API import, separate process peak RSS | 129 MiB | 60 MiB |

In this check the new server used about 72% less idle memory, editor readiness was about 94% faster, and initial transfer was about 97% smaller. These are local observations, not hardware-independent guarantees. Streamlit RSS grows somewhat across browser sessions; the reported range includes the rendered initial session and repeated measurements. RSS does not include the browser or child render processes. The original optional standalone API was **not** running alongside Streamlit, so the baseline is not inflated by two servers.

The browser timings are warm-server navigation with a fresh browser context and empty HTTP cache, measured from navigation until both the script editor and generation control exist. They are not OS-cold startup benchmarks. The legacy onboarding overlay remained in its initial state and no provider configuration was performed. Transfer uses Chromium `Network.loadingFinished.encodedDataLength`; it excludes WebSocket payloads, making the Streamlit estimate conservative. The browser benchmark stops counting at editor readiness and closes after a five-second bounded observation window.

Build output: initial JS about 117 KB / 40 KB gzip; CSS about 14 KB / 3.6 KB gzip. The approximately 10 KB settings module is loaded only when Settings opens. FastAPI compresses static files, but video responses retain native range requests. Bootstrap/schema and existing locale JSON account for the rest of the first load.

## Reproduce

Build and start the replacement as described in [studio.md](studio.md). Start the original from an isolated checkout of `ad5496f`, using an environment with the `legacy-ui` extra:

```sh
python -m streamlit run webui/Main.py --server.address=127.0.0.1 --server.port=8751 --server.headless=true --browser.gatherUsageStats=false
```

From `frontend`, with Playwright Chromium installed:

```sh
npm ci
npx playwright install chromium
node tests/performance.mjs http://127.0.0.1:8080
node tests/performance.mjs http://127.0.0.1:8751 --legacy
```

Run each three times and take the median `readyMs`. Compare `encodedBytes`, and inspect the exact server PIDs with `ps -p PID -o pid,rss,args` after opening each editor. Linux RSS is reported in KiB. Missing browser system libraries require the Playwright prerequisites; this workspace used extracted local test-only libraries, not an application dependency.

To compare API import overhead separately, run the same command in each checkout with the same Python executable:

```sh
/usr/bin/time -f 'elapsed=%e max_rss_kib=%M' python -c 'import app.asgi'
```

The warm sample recorded here was 1.38 s / 132,384 KiB for the original and 0.85 s / 61,392 KiB for the replacement. Import time varies strongly with filesystem cache and does not measure UI navigation.

## Verified boundaries

- Editing and switching already-loaded stages trigger zero API requests (browser regression test).
- Initial server navigation does not import Streamlit, MoviePy, Whisper or provider SDKs (fresh-process regression test).
- A real two-second local-media + uploaded-narration render, background status polling and artifact download passed without external provider calls. Repeat with `MPT_RENDER_SMOKE=1 python -m pytest test/services/test_studio.py -k real_local -q`; the test uses temporary storage.
- Paid integrations are covered by mocks and existing regression tests, not live billable executions. Real accounts, quota and network behavior still need user-side acceptance.
- Docker/Windows launch paths were updated but not executed here: Docker Desktop integration is unavailable in this WSL distro. Raspberry Pi runtime and native optional SDK availability remain hardware-specific acceptance checks.
- Rendering still uses the existing Python/FFmpeg pipeline. This migration reduces idle/UI overhead; it does not promise faster encoding, smaller AI models or lower provider latency.
