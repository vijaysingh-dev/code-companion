import logging

from app.core.config import settings
from app.core.constants import LLMProvider
from app.core.exceptions import ValidationError
from app.models.schema import ModelInfo, ModelsResponse

logger = logging.getLogger(__name__)

# Curated per-provider list of **main-tier** models the client may choose. Each provider's
# mini model is deliberately absent — it is derived server-side from the chosen provider
# (settings.MINI_LLM_MODEL) and never selectable. `supports_effort` flags the models that
# honour the `effort` control (frontier/reasoning models); the rest are steered by
# server-side sampling only. Product config, not wire format — tune freely.
_CATALOG: dict[LLMProvider, list[tuple[str, bool]]] = {
    LLMProvider.OPENAI: [("gpt-5.1", True), ("gpt-4o", False)],
    LLMProvider.ANTHROPIC: [("claude-opus-4-8", True), ("claude-sonnet-5", True)],
    LLMProvider.GOOGLE: [("gemini-2.5-pro", False)],
    LLMProvider.LLAMA: [("llama-3.3-70b-instruct", False)],
}


def list_models() -> ModelsResponse:
    """Main-tier models the client may pick, scoped to the configured provider.

    The mini model is derived server-side, so it is never listed. A pinned main model
    outside the static catalog is still appended, so the configured model is always a
    valid choice and is the one marked `default`.
    """
    provider = settings.LLM_PROVIDER
    current = settings.LLM_MODEL
    catalog = list(_CATALOG.get(provider, []))
    if current not in {model_id for model_id, _ in catalog}:
        catalog.append((current, False))
    models = [
        ModelInfo(id=model_id, supports_effort=effort, default=model_id == current) for model_id, effort in catalog
    ]
    logger.debug("Listed %d models for provider %s", len(models), provider.value)
    return ModelsResponse(provider=provider.value, models=models)


def ensure_allowed(model: str) -> None:
    """Raise if `model` isn't one the configured provider offers for the main tier."""
    allowed = {info.id for info in list_models().models}
    if model not in allowed:
        raise ValidationError(
            message=f"model {model!r} is not available for provider {settings.LLM_PROVIDER.value!r}",
            details={"allowed": sorted(allowed)},
        )
