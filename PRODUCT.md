# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Svelte and TypeScript compiled with Vite; static assets served by the existing FastAPI application. Python and FFmpeg retain the video production pipeline. The user authorized this proposed implementation and requested building directly in code.

## Users

The local operator creates short videos on a PC or a Raspberry Pi and accesses the application in a browser.

## Product Purpose

Turn a topic, supplied script, and chosen media into finished short videos with narration, subtitles, music, and optional publishing.

## Operating Context

Local installation and local-network access. Opening the application and navigating its controls must stay responsive before and during video generation. Node is a build tool, not a production service.

## Capabilities and Constraints

Preserve the existing providers, generation parameters, local uploads, voice samples and full previews, voice cloning inputs, LoomLoom quotes and explicit paid confirmation, task progress and logs, disk history and restoration, presets and credential backup, cache management, localization, batch variants, and optional social publishing. Keep the REST API and CLI compatible. Load expensive media libraries only for operations that need them.

## Brand Commitments

Keep the MoneyPrinterTurbo product name. User-facing collaboration is in Brazilian Portuguese. Existing interface translations remain available.

## Product Principles

- Navigation and form changes run locally in the browser.
- Load optional features when accessed.
- Preserve functionality and security boundaries.
- Verify performance with repeatable measurements.
- Favor native controls and a small dependency set.
