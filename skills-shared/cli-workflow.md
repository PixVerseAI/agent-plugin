# Local Creation And Recovery

Resolve the absolute plugin root from the installed Skill: two directories above its directory.
In each shell session set `PIXVERSE_RUNTIME="<absolute-plugin-root>/scripts/pixverse-runtime"`.
Run commands through `"${PIXVERSE_RUNTIME}"` from the user's working directory. Keep request
receipts and downloaded files under its `projects/` folder. Never delete a receipt to retry.

1. Use `setup` to check readiness; `setup --install` installs the managed npm CLI after checking
   a supported Node.js installation. Python >=3.9 is required; doctor reports the exact
   Node.js and PixVerse CLI requirements. No FFmpeg is needed here.
2. Use `pixverse auth status --json`; when login is needed, use `pixverse auth login` and follow
   `web-handoff.md`. OAuth stays in the CLI and returns a URL without automatically opening a browser.
3. Use `pixverse capabilities create <mode> --model <id> --json` before composing parameters.
   Query `pixverse voice models`, `pixverse music models` or `pixverse template info <id>` as needed.
4. Choose a stable request ID. Run `create --request-id <id> --preflight -- <mode> <options>`.
   Review the returned account, task parameters, blockers and confirmation policy. Stop on blockers.
5. Run the identical command without `--preflight` when allowed. Add `--confirmed` only after the
   user's required approval. Add `--accept-basic-fallback` only for an explicitly accepted fallback.
6. Use `status <id>` (or `recover <id>`) until terminal. Calls are read-only; give progress at least
   every 45 seconds. A host deadline means pending, not failed. Resume with the same request ID.
7. On success use `download <id>` and deliver the returned absolute local paths. A download error
   leaves generation successful; retry download only. No automatic QA or regeneration.

Example after preflight:

```sh
"${PIXVERSE_RUNTIME}" create --request-id mug-image -- image --prompt "A blue ceramic mug on a white studio table"
"${PIXVERSE_RUNTIME}" status mug-image
"${PIXVERSE_RUNTIME}" download mug-image
```

One request owns one independent creation. For an explicitly requested image batch, use a distinct
ID for each composition. Never use dependency placeholders or reinterpret the same ID with changed
arguments/files. If a submission outcome is unknown, preserve the receipt and original account;
inspect existing provider receipts or seek support rather than issuing a replacement. Templates
can return multiple outputs: keep and deliver all receipts, including incomplete responses.

Use `preferences require` or `preferences skip` only for an explicit choice applying to this
workspace's basic requests; add `--global` only for an explicitly global choice.
For authentication, account, catalog and capability reads use the wrapper's `pixverse` command.
Paid creation must use the guarded `create` command. Never bypass it with the raw CLI.
