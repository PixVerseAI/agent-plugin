# PixVerse Agent Plugin

Your AI video and image studio

Create and edit videos and images with PixVerse. Explore visual ideas, refine your
references, and make product photos, character designs, brand visuals and video scripts
through conversation.

PixVerse Agent Plugin brings creative Skills to Claude Code, Cursor, Grok Bot, Pi,
OpenCode, Hermes Agent, and OpenClaw.
Describe what you want to make, provide references when needed, and let your assistant
guide the workflow from prompt to result.

- **PixVerse CLI** runs creative workflows when your assistant has a supported local
  terminal, with downloaded results in your workspace.
- **PixVerse MCP** connects your assistant to the remote PixVerse service when local
  execution is unavailable.

Install for your assistant: [ChatGPT and Codex](#chatgpt-and-codex) ·
[Claude Code](#claude-code) · [Cursor](#cursor) · [Grok Bot](#grok-bot) ·
[Pi](#pi) · [OpenCode](#opencode) · [Hermes Agent](#hermes-agent) · [OpenClaw](#openclaw).

## What You Can Create

The plugin includes six creative Skills:

| Skill | What it does |
| :--- | :--- |
| Image Generation | Create or edit images from prompts and references, including product photos, character references, and visual concepts. |
| Video Generation | Generate video clips from text or images, with supported reference, transition, and transformation modes. |
| Voice Generation | Generate speech from text with your chosen voice and language. |
| Music Generation | Create music from a prompt using the available models and options. |
| Templates and Effects | Browse PixVerse templates, check their required inputs, and generate images or videos. |
| Video Scripts | Write complete scripts, narration, and scene plans without generating media. |

Available models, formats, and reference options depend on the operation and your account.
For additional production workflows, see [ChatGPT and Codex](#chatgpt-and-codex).

## Get Started

You need a [PixVerse account](https://app.pixverse.ai) to generate media. Install the plugin
for your assistant, then sign in when prompted. Authentication uses OAuth; you do not need
to copy an API key or token. Writing a video script does not require an account or tools.

**For local CLI workflows:** Python 3.9 or later and a supported Node.js installation are
required. Ask your assistant to check PixVerse setup. PixVerse Runtime manages the CLI
installation and reports the required Node.js and PixVerse CLI versions.

**For MCP workflows:** connect PixVerse through your assistant and complete authorization.
MCP sign-in and local CLI sign-in are separate; authorize the connection your workflow uses.

## ChatGPT and Codex

Install [PixVerse ChatGPT Plugin](https://chatgpt.com/plugins/plugin_asdk_app_6adab2e460408191a82e46388be67a30)
for either ChatGPT or Codex, then connect your PixVerse account when prompted.

Use it for multi-scene production, Canvas projects, video editing, captions, and timed assembly.
Canvas and advanced finishing require a supported desktop environment.

## Claude Code

Add the repository and install the plugin from your terminal:

```sh
claude plugin marketplace add PixVerseAI/agent-plugin
claude plugin install pixverse@pixverse
```

If you already downloaded or cloned the repository, you can use `./agent-plugin` instead
of `PixVerseAI/agent-plugin` when adding the marketplace from its parent directory.

Start a new Claude Code session and ask PixVerse to check local setup. To connect
PixVerse MCP, open `/mcp` and sign in to PixVerse.

To update:

```sh
claude plugin marketplace update pixverse
claude plugin update pixverse@pixverse
```

## Cursor

Open **Customize** and install PixVerse if it is available in your catalog.

To install directly from this repository:

1. Download or clone the repository.
2. Copy its contents, including hidden files, into `~/.cursor/plugins/local/pixverse/`.
3. Restart Cursor or run **Developer: Reload Window**.
4. Open **Customize** and check that the PixVerse Skills and MCP connection are available.

Sign in through the PixVerse MCP connection when prompted. For local CLI workflows,
ask PixVerse to check local setup. Your organization must allow local plugin imports.
See [Cursor's local installation guide](https://cursor.com/docs/plugins#test-plugins-locally).

## Grok Bot

In **Connect apps**, search for **PixVerse** and install the plugin with its Skills when
available. Complete sign-in, then check that the PixVerse Skills are enabled for your Bot.
Ask your Bot to check PixVerse setup before creating media.

A PixVerse MCP connection alone does not install the Skills. Plugin availability depends
on your catalog and organization settings. See [Grok Bot's connection guide](https://docs.x.ai/grok-bot/computer-and-apps#connect-an-app).

## Pi

Clone the complete repository where Pi runs, keeping `skills-shared/` and `scripts/` alongside the Skills:

```sh
git clone https://github.com/PixVerseAI/agent-plugin.git
```

Add the following to `~/.pi/agent/settings.json`, using your clone's absolute path and
preserving existing settings:

```jsonc
{ "skills": ["/absolute/path/to/agent-plugin/skills"] }
```

Restart Pi and ask it to check PixVerse setup. For a single session, use
`pi --skill /absolute/path/to/agent-plugin/skills`.

If local execution is structurally unavailable, add the following to `~/.pi/agent/mcp.json`
and sign in with `pi mcp login pixverse`:

```jsonc
{ "mcpServers": { "pixverse": { "type": "http", "url": "https://mcp.pixverse.ai/mcp" } } }
```

See [Pi Skills](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/skills.md)
and [Pi MCP](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/mcp.md).

## OpenCode

Clone the complete repository where OpenCode runs, keeping `skills-shared/` and `scripts/` alongside the Skills:

```sh
git clone https://github.com/PixVerseAI/agent-plugin.git
```

Add the following to `~/.config/opencode/opencode.json`, using your clone's absolute path
and preserving existing settings:

```jsonc
{ "skills": { "paths": ["/absolute/path/to/agent-plugin/skills"] } }
```

Restart OpenCode, verify discovery with `opencode debug skill`, and ask it to check PixVerse setup.
If local execution is structurally unavailable, add the following to the same config and
run `opencode mcp auth pixverse`:

```jsonc
{ "mcp": { "pixverse": { "type": "remote", "url": "https://mcp.pixverse.ai/mcp", "enabled": true } } }
```

See [OpenCode Skills](https://opencode.ai/docs/skills/) and
[OpenCode MCP](https://opencode.ai/docs/mcp-servers/).

## Hermes Agent

Clone the complete repository where Hermes runs, keeping `skills-shared/` and `scripts/` alongside the Skills:

```sh
git clone https://github.com/PixVerseAI/agent-plugin.git
```

Add the following to `~/.hermes/config.yaml`, using your clone's absolute path and
preserving existing settings:

```yaml
skills:
  external_dirs:
    - /absolute/path/to/agent-plugin/skills
```

Restart Hermes, check discovery with `hermes skills list`, and ask it to check PixVerse setup.
Give Hermes the repository path so it can read the shared files from the local filesystem;
`skill_view` only opens files inside a Skill directory.
If local execution is structurally unavailable, add the following to the same config and use
`hermes mcp login pixverse` to authorize:

```yaml
mcp_servers:
  pixverse:
    url: https://mcp.pixverse.ai/mcp
    auth: oauth
```

See [Hermes Skills](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/skills.md)
and [Hermes MCP](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/mcp.md).

## OpenClaw

Clone the complete repository where OpenClaw runs, keeping `skills-shared/` and `scripts/` alongside the Skills:

```sh
git clone https://github.com/PixVerseAI/agent-plugin.git
```

Add the following to `~/.openclaw/openclaw.json`, using your clone's absolute path and
preserving existing settings:

```jsonc
{ "skills": { "load": { "extraDirs": ["/absolute/path/to/agent-plugin/skills"] } } }
```

Restart OpenClaw, check discovery with `openclaw skills list`, and ask it to check PixVerse setup.
If local execution is structurally unavailable, add the following to the same config,
then authorize through **Settings → MCP** or
`openclaw mcp login pixverse` (follow OpenClaw's Gateway instructions for CLI login):

```jsonc
{ "mcp": { "servers": { "pixverse": { "url": "https://mcp.pixverse.ai/mcp", "transport": "streamable-http", "auth": "oauth" } } } }
```

See [OpenClaw Skills](https://docs.openclaw.ai/tools/skills) and
[OpenClaw MCP](https://docs.openclaw.ai/tools/mcp).

## Usage

Ask your assistant in natural language:

- "Create one studio product image of a matte blue ceramic mug."
- "Animate my reference image as one five-second clip with a slow camera move."
- "Generate speech saying: A warm cup. A better morning."
- "Create a gentle piano instrumental for a coffee shop, with no vocals."
- "Browse three effect templates and explain the inputs for the first. Do not generate yet."
- "Write a complete 30-second product video script. Do not generate media."

Your assistant checks the supported options, follows generation progress, and returns
previews, links, or downloaded files according to its available tools.

If a connection or preview is interrupted, ask it to check the existing generation.
A missing preview or expired download link does not require a new generation.
Authentication, credit, or generation errors pause the workflow so the issue can be resolved
without switching connections or automatically submitting another generation.

## Account and Credits

Media generation uses credits from your PixVerse account. Model and feature access depends
on your subscription; see [PixVerse Subscription Plans](https://app.pixverse.ai/subscribe).
Your assistant checks account access and credits before generation, and asks before switching
to a lower-quality alternative. Writing a script does not generate media or use generation credits.

## Other MCP Clients

Add the PixVerse MCP server to an MCP-compatible client and sign in with PixVerse:

```json
{
  "mcpServers": {
    "pixverse": {
      "type": "http",
      "url": "https://mcp.pixverse.ai/mcp"
    }
  }
}
```

The server provides PixVerse tools. Installing PixVerse Agent Plugin also adds the creative
Skills in this repository. Keep one active PixVerse MCP connection in each assistant
to avoid duplicate tools.

## Support

- [PixVerse Documentation](https://docs.pixverse.ai/PixVerse-Official-Guides-6e66b59c781746839f76ad84ef6ddf82)
- Email: support@pixverse.ai
- [Privacy Policy](https://pixverse.ai/en/privacy-policy)
- [Terms of Service](https://pixverse.ai/en/terms-of-service)

## License

Plugin files are available under the [MIT License](./LICENSE).
Use of the PixVerse service is governed by PixVerse's Terms of Service.
