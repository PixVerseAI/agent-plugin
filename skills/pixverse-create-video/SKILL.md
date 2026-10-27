---
name: pixverse-create-video
description: "Generate or transform a video clip from text, images or supported media references. Use for a requested clip, animation, extension, restyle or upscale."
---

# Create Video

## Execution Surface

Read `../../skills-shared/execution-surface.md` before execution. Prefer a usable managed CLI; local execution follows `../../skills-shared/cli-workflow.md`.
In MCP mode, read `../../skills-shared/mcp-workflow.md` and follow the MCP scope below.
Do not execute the local setup, queue, filesystem, QA or finishing instructions below in MCP mode.
Script-only work needs no login or tools.

### MCP Scope

Generate or transform clips using a live-supported mode and model. Preserve every reference and its role; do not silently replace multi-reference work with first-frame generation. Model-generated edits do not guarantee frame-exact timing, cuts or source detail. This scope does not include timeline assembly or transcription.

Choose the supported mode matching the requested result: video, reference, transition, extend, modify, upscale or motion-control. Use capabilities for required inputs and limits. Default supported video generation to seedance-2.5 at 1080p. A simple clip is one direct video task. If the requested result requires a control image, explain the additional scope before paid execution and follow the shared confirmation policy.

For execution, read `../../skills-shared/execution-surface.md`. It selects the supported CLI or MCP branch, checks account and quality requirements, and preserves submission identity through delivery.