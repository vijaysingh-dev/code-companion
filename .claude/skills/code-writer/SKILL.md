---
name: code-writer
description: 'Use this skill whenever writing or editing implementation code in the Code Companion repo — Python/FastAPI (app/) or TypeScript (extension/). Triggers on any request to add or change a router, service, pydantic model, middleware, extension command, webview, or provider, or to refactor existing code. Use it even when the request does not say "follow conventions". Respects backend-first phasing: backend is written before the extension consumes it.'
---

# code-writer

The "how the implementation is written" standard for Code Companion. Read `CLAUDE.md` for project facts (layout, phase, conventions). This file is the quality checklist, not a project description — don't duplicate project facts here.

## Workflow: phases

**No automated tests yet.** Don't write or expect a test suite. Verify by reading the code and running `ruff`/`mypy` (and the app manually when useful).

**Phase order — backend first.** A slice is built in `app/` before the `extension/` consumes it. Don't write extension code against a backend endpoint that isn't done. Backend order within a slice: **schema (pydantic) → service → router**.

**AI runs the mechanical steps:** `ruff check`/`ruff format`, `mypy app/`. The human decides phase transitions.

## Core principle

**Copy > paste > modify — never reinvent.** When a pattern already exists in the repo, copy the closest implementation and change only what differs. A new router copies an existing one in `app/api/`; a new service copies a sibling in `app/services/`.

**Simplicity first:** write the simplest thing that solves the need in front of you — no abstraction, configurability, or generality for hypothetical futures. Add complexity only when the simple version genuinely won't hold, or a concrete roadmap phase requires it; "we might need it" is not a reason. Prefer flat module-level functions and mini files over class hierarchies. Use a design pattern (Strategy for `Chunker`/`Retriever`/`LLMProvider`, Factory for config→impl) only where it removes real duplication — the roadmap calls these out; introduce them when that phase arrives, not preemptively. Between two correct solutions, pick the one a junior could read without explanation.

## Architecture rules (must follow)

- **Service layer.** Domain logic lives in `app/services/`, not in routers. Routers own only HTTP: parse request → call service → shape response.
- **Unversioned API.** No `/v1`. Add a router, include it in `app/api/router.py`; it mounts under `settings.API_PREFIX`.
- **Config.** All env reads go through `settings` (`app.core.config`). Never call `os.getenv`/`os.environ` in app code.
- **BASE_DIR.** Import `from app.core.constants import BASE_DIR`. Never recompute paths with `Path(__file__).parent...` outside `constants.py`.
- **Keep core generic.** `app/core/` (config, logging, constants, application, exceptions) and `middleware/` are the reusable skeleton — don't put Code-Companion domain logic there.

## Python style (app/) — `ruff check app/ && mypy app/`

Ruff + Mypy, line 120, double quotes, space indent. Ruff set `E, W, F, I, UP, B, SIM`; `E501` ignored at lint but the formatter still wraps at 120 — don't hand-write long lines. isort first-party = `app`.

- **Logging — every file, every edit.** Every Python file created or edited has a module-level `logger = logging.getLogger(__name__)` — never a hardcoded name. Log key operations: `debug` for routine flow, `info` for state transitions, `warning` for recoverable anomalies, `error` for failures. Applies to every file touched, not just new ones.
- **Typing.** Annotate **every** function/method signature. Use `X | None` (not `Optional[X]`), `X | Y` unions, `dict[str, Any]` (never bare `dict`). Don't silently return `Any` (`warn_return_any` + `no_implicit_reexport` are on). Import `Any` from `typing` when needed.
- **Errors.** Raise a specific `CodeCompanionException` subclass from services; the exception handler (`app/middleware/error_handler.py`) turns it into the JSON error envelope. Don't signal failure with `None` where an exception is clearer. Error responses use `create_error_response` — don't hand-build error dicts in routers.
- **Async.** Endpoints and services that do I/O are `async def`. Don't block the event loop with sync I/O.

## TypeScript style (extension/) — `npm run compile`

VS Code extension, `tsc` strict, Prettier printWidth 120, ESLint flat config.

- **Follow the VS Code extension idioms** already in `extension/src/` — copy the nearest command/panel/service rather than inventing structure. Register commands and disposables into `context.subscriptions`.
- Type everything; no implicit `any`, no unused locals/params (tsconfig strict).
- Keep the backend contract in sync: the extension calls the FastAPI endpoints — request/response shapes must match `app/models/schema.py`. When the backend schema changes, update the extension's types to match; don't let them drift.
- No `console.log` left in committed code; use the extension's output channel / proper error surfacing.

## Comment discipline (strict)

- **Default to none.** Most code needs no comments — a well-named function/variable beats a comment. When in doubt, leave it out.
- Add one only where intent genuinely isn't recoverable from the code, and keep it to **one concise line** stating *why* (the non-obvious constraint), never narrating *what*. Bad: `# loop through files`. OK: `# site-packages frames fall back to the logger name, not an absolute path`.
- No line-by-line, no comment-per-block, no section banners, no commented-out code.
- Future work goes in a single-line `# TODO: <what>`. Nothing else in TODO form.

## Self-check before presenting any diff

1. **Service layer:** domain logic in `app/services/`, routers thin?
2. **Duplication:** did I re-implement something already in `app/services/`, `app/core/`, or the extension — in any layer?
3. **Phase:** right phase? No extension code against a backend that isn't done + green?
4. **Config/paths:** env via `settings`, `BASE_DIR` imported from `constants` (no `os.getenv`, no recomputed paths)?
5. **Gates:** `ruff check`/`ruff format`/`mypy app/` clean? (extension) `tsc` clean?
6. **Logging:** every Python file I touched has `logger = logging.getLogger(__name__)` and meaningful log calls?
7. **Typing:** every signature annotated, no silent `Any`, `X | None` not `Optional`?
8. **Comments:** defaulted to none; any kept one is a concise one-liner explaining *why*, not narrating? Future work as `# TODO: <what>`?
9. **Minimal change:** flattest correct version, no premature abstraction or pattern that doesn't earn its place?
10. **Skeleton kept generic:** did I avoid leaking domain logic into `app/core/` / `middleware/`?
11. **Contract sync:** if I changed `app/models/schema.py`, did the extension's request/response types follow?
12. **CLAUDE.md drift:** if I added a module/convention or moved a roadmap slice to "current", is the matching CLAUDE.md update in this diff?

After presenting the diff, stop and hand back to the human.
