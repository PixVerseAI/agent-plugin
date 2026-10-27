---
name: pixverse-create-image
description: "Create or edit images from a prompt and optional references. Use for a requested image, product photo, character reference, illustration or visual edit."
---

# Create Images

## Execution Surface

Read `../../skills-shared/execution-surface.md` before execution. Prefer a usable managed CLI; local execution follows `../../skills-shared/cli-workflow.md`.
In MCP mode, read `../../skills-shared/mcp-workflow.md` and follow the MCP scope below.
Do not execute the local setup, queue, filesystem, QA or finishing instructions below in MCP mode.
Script-only work needs no login or tools.

### MCP Scope

Generate or revise still images with owned identity references. Query live capabilities, check the account, submit each agreed composition and deliver every output. Preserve requested text without guaranteeing exact typography or pixel layout.

Preserve the requested subject, reference roles, layout and format. Describe the visible result clearly. Default to gpt-image-2.5-sunburst at 1440p with high detail. Use separate requests for independent compositions; do not introduce video tasks.

For execution, read `../../skills-shared/execution-surface.md`. It selects the supported CLI or MCP branch, checks account and quality requirements, and preserves submission identity through delivery.