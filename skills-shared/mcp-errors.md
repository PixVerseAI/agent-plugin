# MCP Error Handling

This is a host conversation contract, not an executable cloud dependency. Apply it on
supported MCP hosts with the same account and generation gates.

## Read The Actual Failure

Check MCP `isError`, JSON-RPC errors, HTTP authentication challenges, import `error_code`,
and terminal task status. HTTP 200 does not prove business success. The current backend
returns business failures as text such as `PixVerse API error 500323: ... (trace_id=...)`;
authentication failures may instead say `authorization is no longer valid (code 10003)`.
Do not require an imagined structured error object. Prefer an explicit returned code to
message matching. Preserve original Unicode messages and exact IDs in recovery context;
explain the actionable cause in the user's language. Do not translate or alter input
references to make an error disappear.

| Code / evidence | Meaning | Conversation action |
|---|---|---|
| HTTP 401, OAuth challenge, 10001-10005, explicit expired/revoked authorization | Connection or account authorization unavailable | Stop paid work; reconnect through host OAuth, then refresh account. If the message says blocked/deleted, explain that account condition and offer support rather than looping reconnect. |
| 400024, 500215, explicit blocked/deleted account | Account restricted or pending deletion | Stop; explain the returned restriction and use the returned support guidance. Reauthorization or upgrade is not a promised fix. |
| 500323 | External model requires a qualifying paid tier | Stop remaining paid tasks; explain the selected model's restriction and link subscription. Non-basic membership alone does not guarantee access. |
| 500342 | Image model requires Standard or higher | Stop; explain the image model's tier restriction. Offer upgrade or an explicitly accepted supported fallback, never silently substitute. |
| 500608 | Feature unavailable to non-members | Stop; explain the feature restriction; offer upgrade or a supported alternative only with consent. |
| 500340 | Upgrade begins next billing cycle | Explain that premium access is not active yet; do not promise immediate access after payment or keep retrying. Refresh account when the user reports the plan is effective. |
| 500043, 500090, 666666 | Insufficient credits | Stop the batch; offer subscription/recharge. A cheaper model is not guaranteed to fit the balance or be free. |
| 500108 | Daily free credits used | Explain the returned daily reset guidance or offer recharge. Do not invent a timezone or reset timestamp. |
| 500930, 500931, 500932 | Team credits, personal cap, or guest spending restriction | Follow the returned owner/admin guidance; a personal subscription link is not automatically the solution. |
| 500044, 500094, HTTP 429 with matching concurrency/rate message | Concurrent-generation or rate limit | Keep accepted task IDs and cards; wait for those tasks. Do not resubmit them or label queued work failed. A new submission requires evidence of non-acceptance and the original stable key/retry rules. |
| 500069 | Service busy | Explain temporary capacity limits. Do not silently change transport/model or assume a failed create was never accepted. |
| 400039, 500321, 500322, 500324, 500325, 500326 | Deprecated model or unsupported quality/parameters/duration/ratio | Explain the actual rejected field using the live schema/server message. Preserve explicit requirements; ask for an alternative when it materially changes the result. No repeated identical invalid request. |
| 400040, 500054, 500063, task `rejected` | Content/reference moderation rejection | Explain the returned cause, stop dependent work, and request an appropriate revision. No automatic evasion or paid replacement. |
| 500047, 500085, unowned path/ID, invalid import | Invalid, unavailable or foreign asset | Keep references; verify the exact task/account or recover/import the authorized source. Do not discard references or switch to prompt-only generation. |
| 500313 while loading a known task | Generic detail lookup failure; not proof of generation failure | Check exact ID and connection; briefly retry read-only status if just submitted. Never regenerate a task to repair status loading. |
| Timeout, connection loss, 5xx without a decisive business code | Transport/service uncertainty | Read-only recovery first. A create may have been accepted: preserve its key, arguments and IDs; follow the route-specific recovery contract in the MCP workflow. |
| Media load, host download or expired attachment failure | Delivery failure | Preserve the successful task. Refresh the existing card or request a fresh temporary URL using download_media; never pay for regeneration to repair delivery. |

When only a message is available, distinguish authentication, membership, insufficient
credits, concurrency, invalid parameters and delivery using its explicit meaning, including
upstream non-English messages. Ambiguous words such as `permission`, `network` or `free`
alone do not establish a category. `free generation` for an entitled paid plan is not
the same as `member_type: 0`. A schema enum is not an entitlement grant.

## Free/Basic Choices

For `member_type: 0`, preserve premium defaults but pause before submitting them. Show
the [PixVerse subscription/recharge page](https://app.pixverse.ai/subscribe) and offer
upgrade or an explicit lower-quality route: Nano Banana 2 Lite (`gemini-3.1-flash-lite`)
at `1080p` for images, or v6 at `540p` for video. Describe these as fallback candidates,
subject to the live schema, credits and backend permission; never promise every free
account can run them or that they cost zero. An explicit user selection of that model
and quality is consent for that route. Keep uploaded/product/character references.

Unknown membership pauses. Paid membership still requires server entitlement. After
an upgrade, read account again before new generation; if the backend still rejects the
model or says next billing cycle, explain that result and stop. A previously accepted
fallback is not consent to replace a later explicitly requested premium model.

Keep replies concise: what was blocked, whether any tasks were already accepted, and
the concrete available next action. Preserve successful cards in a partial batch; stop
remaining submissions on entitlement/credit rejection. No CLI fallback, host shell,
credential request, invented quote, or extra preview card is part of error recovery.
