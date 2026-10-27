# MCP Workflow

Use this branch only after `execution-surface.md` selects MCP. Call the host's registered
PixVerse tools directly; never run shell commands, raw HTTP, `pixverse-runtime` or a cloud executor.
Host OAuth owns credentials. A manifest URL alone does not establish a callable connection.
If tools are missing, enable/connect PixVerse through the host. Authentication errors require
reconnection and an account check, never token extraction or transport fallback.
For browser or local-login handoffs, follow [Browser handoffs](./web-handoff.md).

## Scope And Live Discovery

Follow the generated **MCP Scope** in the selected Skill. A desktop-only entry must stop
before its local production instructions. More service tools do not expand a Skill's scope.
Do not silently reduce a finished-film request to raw clips; obtain agreement on a supported result.
Script-only work needs no login or generation. MCP does not grant shell, Canvas, local inspection,
project storage or arbitrary asset-management capabilities.

Tool names below describe workflow roles; resolve their actual host namespace and live schema.
Use the current tools' descriptions and input schemas for fields, types and required arguments.
Use `capabilities` for the selected image/video mode and model, `audio_catalog` for music or
voice choices, and `template` detail for selected templates. Inspect conditional requirements,
reference support and pagination. Never infer an interface from CLI flags or a remembered schema.
The live contract overrides snapshots; stop on a material mismatch. Check only tools required by
the requested outcome, rather than demanding a fixed tool inventory or count.

## Quality, Account And Spending

Before each paid batch read `account`. Retain identity, member_type, credits, planned output
count and exact parameters. Basic/Free is member_type 0; the known paid levels are 1..11.
Unknown membership or balance stops new submissions. Paid membership alone does not prove
model entitlement. After an upgrade or account correction, refresh the account before continuing.
Use `quality-policy.md` and `mcp-errors.md`; preserve the configured defaults and prompt guidance.
Only explicit fallback consent permits a quality downgrade, with all references retained.
An entitlement or balance rejection stops remaining submissions, without transport fallback.
Audio and template choices require their actual catalog/entitlements, not an invented fallback.
A simple video with unspecified duration defaults to five seconds where the selected mode supports it.

There is no MCP price quote for generation. State scope and planned generation count, then proceed
under default skip. Honor a request to confirm each batch; obtain approval before submitting
under require. A hard generation spending ceiling cannot be guaranteed without a quote: stop
rather than promise it fits. Conversation memory does not set persistent project/global preferences.

## References And Submission

Preserve every supplied reference, its type, order and intended role. Use existing owned IDs or
import authorized media through the host's available import tools. Follow their live input schema;
never fabricate attachment download URLs, pass local paths as cloud assets, expose signed source
URLs or fetch private networks. If the host provides no usable handoff, request an accessible source.
Wait for import completion and retain the owned asset ID before submitting dependent generation.
A failed import stops dependents. Importing media does not establish model reference support.

Create a stable unique client_request_id per intended submission and retain its exact arguments
before calling the matching creation tool. Preserve the agreed scope and output count; default to
one output unless the user requests more. Separate compositions need separate prompts/submissions.
Keep ALL returned task IDs, media types, request identities, trace IDs and cost receipts.
Keep IDs as exact strings. Never round IDs through JavaScript Number or confuse owned asset IDs,
generation IDs and editing operation IDs. Deliver every template output, including mixed media.

Immediately after submission returns task IDs, call render_media once for every unique image,
video or audio task on MCP Apps hosts, before waiting for completion. This includes every template output.
Show the accepted task immediately; the same card automatically updates to completion or failure.

## Waiting And Recovery

Keep the original connection, account, region and request identity through recovery. Prefer
read-only generation_status with string IDs, or audio_status for audio, whenever task IDs exist.
Honor the live tools' wait and recovery limits. Queued/processing states are not failures.
Provide progress at least every 45 seconds. At a host deadline, give a pending receipt and resume
existing IDs later. Terminal failures stop dependent tasks.

For an uncertain submission, retain its key and exact payload. Do not change keys, create another
task or assume indefinite idempotency. Use only recovery/replay behavior explicitly supported by
the live tool contract, within its stated validity window; otherwise stop and report uncertainty.
Audio history can help find an owned result, but similar text/model/time alone does not prove identity.
Do not invent a lookup-by-request-key tool. An intentional retry of a terminal failure is a new
paid batch under the same account, scope and confirmation rules. Count each accepted receipt once.

## Delivery

This is the plugin's presentation policy: on MCP Apps hosts, live cards are required.
The service's neutral tool descriptions do not relax this plugin's live-card requirement.
Invoke the registered render_media tool; the host renders the tool's registered UI resource.
Do not construct an iframe, execute widget HTML or fabricate local paths.
Keep one card per accepted task; status polling must not create duplicate cards.
A successful status response or a URL does not replace a working card. If the renderer is
unavailable or the host cannot load its UI, explain the actual limitation and use the result URL.
Do not infer lack of UI support merely because the renderer was not called.
Recover a missing card read-only; never regenerate to repair display or download failures.

Use download_media for requested file delivery or expired-link recovery. It returns a temporary
URL, not an automatic local download. Preserve completed outputs through delivery failures.
Only claim properties actually observed; codecs, exact timing, caption sync and local files remain
not_checked without evidence. No automatic shell QA or post-generation balance query is required.
