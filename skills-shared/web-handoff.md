# Browser Handoffs

Use the exact URL returned by PixVerse Runtime for OAuth and subscriptions. Use a browser control explicitly available in the current
host, or provide the clickable link for the user to open. Do not assume a particular
browser tool, inspect unrelated tabs, transfer credentials or open a system browser
automatically.

## OAuth

A connected MCP account does not automatically authenticate the local PixVerse CLI.
Reuse a valid CLI login. If login is missing, follow the flow below.

Run `"${PIXVERSE_RUNTIME}" pixverse auth login --json` in a pollable process. Show the
complete returned authorization URL immediately and keep the process alive while the
user signs in. After it completes, check CLI authentication and the selected account.
Do not ask the user to paste tokens, cookies or OAuth callbacks into the conversation.
Do not copy MCP credentials into the CLI or invent a host authorization tool.

Before generation, check the local CLI account and available credits. When both
transports are connected, resolve any account mismatch before submitting. A login,
entitlement, credit or generation error is not a reason to switch transport.
An accepted or ambiguous submission keeps its original account, transport, request ID
and task IDs through status recovery and delivery.

CLI authentication and the browser's signed-in web session are separate. On a login
redirect, ask the user to sign in and return to the original page in that same session.
Do not log out or clear either session solely because the plugin was updated.
