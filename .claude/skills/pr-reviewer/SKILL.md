---
name: pr-reviewer
description: Use this skill to review a code change (diff) before the human reviews it, in the Code Companion repo. Triggers when a change — code plus its tests — is ready for review, at the end of the TDD loop, or when the user asks to "review", "check", or "look over" a diff. This is an INDEPENDENT pass, separate from the skill that wrote the code, so it catches what the author missed. Invoke it only when there's an actual diff to review (not preemptively), to conserve LLM usage.
---

# pr-reviewer

The independent check in the AI-writes / human-reviews loop. Its value is being a _fresh pass_ — do not assume the just-written code is correct. Read `CLAUDE.md` for facts, layout, and current phase. The shared **workflow block** (modes, backend-first phases, AI/human division) lives in `code-writer`. Review **code and tests together** — in TDD a change is incomplete without both.

This does **not** replace human review — it makes it cheaper by surfacing what deserves a closer look. Reason about the diff; **don't run the suite or tools yourself unless asked** (the human runs them). End every review by naming what the human should personally verify.

## How to review

In order. Group findings as **Blocking**, **Should fix**, **Note**. Be concrete: point at the line/function, say why, suggest the fix.

### 1. Does it do what was asked?

Diff vs stated intent. Missing cases? Misread requirement? For a bug fix, is there now a test that locks the bug out?

### 2. Test quality (critical in TDD)

When one pass wrote both test and code, the test can be shaped to assert whatever the code does — proving nothing. Check:

- Do tests assert **intended behavior** or just mirror the implementation?
- Would they **fail if the implementation were wrong**? (Mentally break the code — would a test catch it?)
- Negative cases present: invalid input (422), missing resource (404), error paths?
- Any tautological, over-mocked (mocking the service under test), or incidental-detail assertions?

### 3. Architecture & conventions

- **Service layer:** domain logic in `app/services/`, routers thin? Flag logic leaked into a router.
- **API:** unversioned, mounted via `app/api/router.py` under `settings.API_PREFIX`? No stray `/v1`?
- **Config:** any direct `os.getenv`/`os.environ` instead of `settings`?
- **Paths:** any `Path(__file__).parent...` recomputation instead of importing `BASE_DIR` from `constants`?
- **Skeleton kept generic:** did domain logic leak into `app/core/` or `middleware/` (the reusable skeleton)?
- **Contract sync:** if `app/models/schema.py` changed, do the extension's request/response types match?
- **Duplication:** re-implements something already in `app/services/`, `app/core/`, or the extension? Point to it.
- **Phase:** is extension code appearing against a backend that isn't done + green? Flag it.
- **Premature abstraction:** a Strategy/Factory/config layer introduced before the roadmap phase that needs it, or before there's real duplication to remove? Flag it.

### 4. Style & quality gates

- Would `ruff check`/`ruff format`/`mypy app/` pass (line 120, double quotes)? (extension) `tsc` strict, ESLint, Prettier?
- **Python logging:** does every touched `.py` file have `logger = logging.getLogger(__name__)` (never a hardcoded name) and meaningful log calls?
- **Typing:** signatures annotated, no silent `Any`, `X | None` not `Optional`, imports sorted (first-party `app`)?
- **Errors:** services raise `CodeCompanionException` subclasses; routers don't hand-build error dicts?
- **Async:** I/O paths are `async`, no blocking calls on the event loop?
- **Comments:** sparse, descriptive (what/why), non-instructional? Flag narration, line-by-line comments, commented-out code, stray TODOs (a `# TODO(Sx.y)` roadmap pointer is fine).
- **TS:** no leftover `console.log`, no implicit `any`, no unused locals/params.

### 5. Security & data integrity

- Input validated by the pydantic model — no trust of client-supplied paths/ids?
- No secrets/keys/env values committed? (LLM API keys come from `settings`, never hardcoded.)
- File-system access (indexing/ingestion) stays within intended roots — no path traversal from user input?

### 6. CLAUDE.md upkeep

If the change adds a module/package, makes or reverses a decision, adopts a convention, or moves a roadmap slice to "current" — is the matching CLAUDE.md update included? If not, flag and draft it.

## Output format

```
## Review summary
<1–2 sentences: what it does, overall assessment>

## Blocking
- ...
## Should fix
- ...
## Notes (learning / optional)
- ...

## For the human to verify
<the one or two things worth a human's eyes>
```

Be honest and direct — the developer wants real critique, not reassurance. Don't pad. If nothing is blocking, say so plainly.
