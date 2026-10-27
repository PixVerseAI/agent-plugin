---
name: pixverse-create-voice
description: "Generate speech from supplied or approved text, voice and language. Use for a standalone speech asset."
---

# Create Voice

## Execution Surface

Read `../../skills-shared/execution-surface.md` before execution. Prefer a usable managed CLI; local execution follows `../../skills-shared/cli-workflow.md`.
In MCP mode, read `../../skills-shared/mcp-workflow.md` and follow the MCP scope below.
Do not execute the local setup, queue, filesystem, QA or finishing instructions below in MCP mode.
Script-only work needs no login or tools.

### MCP Scope

Generate standalone spoken narration or explicitly requested separate takes. Preserve exact text, language and pronunciation; discover actual voice/model IDs. Deliver returned timing metadata without inventing alignment. No dubbing, forced alignment, exact-window repair or automatic concatenation.

Preserve the spoken text, language and pronunciation requirements. Discover actual voice IDs and supported voice models. Ask only for material missing choices. Deliver the speech asset; measured timing, revoicing and timeline alignment require the production workflow.

For execution, read `../../skills-shared/execution-surface.md`. It selects the supported CLI or MCP branch, checks account and quality requirements, and preserves submission identity through delivery.