---
name: pixverse-create-music
description: "Generate music for a requested mood, scene or brief, including background music and songs. Use pixverse-create-voice for spoken narration."
---

# Create Music

## Execution Surface

Read `../../skills-shared/execution-surface.md` before execution. Prefer a usable managed CLI; local execution follows `../../skills-shared/cli-workflow.md`.
In MCP mode, read `../../skills-shared/mcp-workflow.md` and follow the MCP scope below.
Do not execute the local setup, queue, filesystem, QA or finishing instructions below in MCP mode.
Script-only work needs no login or tools.

### MCP Scope

Generate standalone music using live music models and supported lyrics or instrumental controls. Spoken narration belongs to pixverse-create-voice. Do not promise dedicated SFX generation, mixing, trimming, fades or exact-duration soundtracks through music generation.

Discover supported music models and input fields from the current catalog. Describe mood, instrumentation, energy, desired duration and any supplied lyrics. Do not invent voices, exact timing guarantees or unsupported sound-generation modes.

For execution, read `../../skills-shared/execution-surface.md`. It selects the supported CLI or MCP branch, checks account and quality requirements, and preserves submission identity through delivery.