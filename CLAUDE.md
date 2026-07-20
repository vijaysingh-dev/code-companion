# Code Companion

An agent-first VS Code coding assistant, like Claude Code. Two parts in one repo:

- **`app/`** — FastAPI backend (Python 3.10). The engine: chat, the agent tool loop, providers, and (later, optional) retrieval.
- **`extension/`** — VS Code extension (TypeScript). The client: chat panel, commands, talks to the backend.

The build plan lives in [roadmap.md](roadmap.md) — agent-first vertical slices (Phase 0 skeleton → agent loop → edit/run → any-LLM → cheaper/faster → eval → then RAG as a measured experiment). The heart is the **agent tool loop**, not RAG; RAG is an optional, evaluated branch. The old RAG-first plan is kept for reference in [.archive/roadmap.md](.archive/roadmap.md). **We are at Phase 0:** a walking skeleton (extension ↔ FastAPI ↔ chat). `app/services/chat.py` currently returns a stub; swapping it for a real LLM call is S0.2.

This backend is also a **reusable FastAPI skeleton** — keep the core (`config`, `logging`, `constants`, `application`, middleware, exceptions) generic and project-agnostic. Project-specific code lives in `api/`, `services/`, and `models/`.

## Layout

```
app/
  main.py            create_application(): app factory + lifespan
  core/
    constants.py     BASE_DIR (repo root) — import BASE_DIR from here, never recompute
    config.py        Settings (pydantic-settings), env via .env; import `settings`
    logging.py       RelativePathFormatter + setup_logging() (dictConfig)
    application.py    Application: process-wide service lifecycle (start/stop)
    exceptions.py    CodeCompanionException hierarchy
  api/               HTTP layer — routers only, thin. router.py aggregates (no version prefix)
  services/          domain logic lives here, not in views
  models/schema.py   pydantic request/response models
  middleware/        request logging + exception handlers
extension/           VS Code extension (own package.json, tsconfig, .vscode/)
```

## Conventions (backend)

- **BASE_DIR**: defined once in `app/core/constants.py` as the repo root. Import it (`from app.core.constants import BASE_DIR`) — do not write `Path(__file__).parent...` elsewhere.
- **Config**: all env reads go through `settings` (`app.core.config`). Never call `os.getenv` in app code.
- **Logging**: every module has `logger = logging.getLogger(__name__)` — never a hardcoded name. `setup_logging()` runs once in the app factory. Logs render as `LEVEL <iso-time>.<ms> <path>:<line> - message`, where `<path>` is relative to BASE_DIR via `RelativePathFormatter`.
- **Service layer**: domain logic goes in `app/services/`; routers only parse → call service → shape response.
- **API is unversioned** — no `/v1`. Add routers to `app/api/router.py`; they mount under `settings.API_PREFIX` (`/api`).
- **Style**: Ruff + Mypy, line 120, double quotes, `X | None` (not `Optional`). Annotate every signature.

## Commands

Backend (from repo root, venv active):
```bash
pip install -r requirements.txt -r requirements.dev.txt
uvicorn app.main:app --reload          # run (http://127.0.0.1:8000, docs at /docs)
python -m ruff check app/ && python -m ruff format app/
python -m mypy app/
```

Extension (from `extension/`):
```bash
npm install
npm run watch      # or: npm run compile
npm run package    # vsce package → .vsix
```
Press **F5** (Run Extension) from the `extension/` folder to launch an Extension Development Host.

## Git

Conventional Commits are enforced by `.githooks/commit-msg`; `.githooks/pre-commit` runs `make check`. Enable with `git config core.hooksPath .githooks`. (No Makefile yet — add one or adjust the hook before relying on pre-commit.)
