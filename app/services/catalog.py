import logging
from functools import lru_cache

import yaml
from pydantic import BaseModel, model_validator

from app.core.constants import BASE_DIR, LLMProvider
from app.core.exceptions import ValidationError
from app.models.schema import ModelInfo, ModelsResponse

logger = logging.getLogger(__name__)

_CONFIG_PATH = BASE_DIR / "config.yaml"


class ModelEntry(BaseModel):
    id: str
    effort: bool = False


class ProviderEntry(BaseModel):
    provider: LLMProvider
    name: str
    api_key: str = ""
    base_url: str | None = None
    # Azure only: base_url is the resource endpoint, api_version is required, and each
    # model id is a deployment name.
    api_version: str | None = None
    # Bedrock only: SigV4 auth (no api_key); model ids are Bedrock model identifiers.
    region: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_session_token: str | None = None
    max_tokens: int = 2048
    mini_model: str
    models: list[ModelEntry]

    @model_validator(mode="after")
    def _check_credentials(self) -> "ProviderEntry":
        if self.provider is LLMProvider.AZURE:
            if not (self.base_url and self.api_version):
                raise ValueError("azure provider requires base_url and api_version")
        elif self.provider is LLMProvider.BEDROCK:
            if not (self.region and self.aws_access_key_id and self.aws_secret_access_key):
                raise ValueError("bedrock provider requires region, aws_access_key_id, aws_secret_access_key")
        elif not self.api_key:
            raise ValueError(f"{self.provider.value} provider requires api_key")
        return self


class Catalog(BaseModel):
    providers: list[ProviderEntry]


class ResolvedModel(BaseModel):
    provider: LLMProvider
    provider_name: str
    model: str
    api_key: str
    base_url: str | None
    api_version: str | None
    region: str | None
    aws_access_key_id: str | None
    aws_secret_access_key: str | None
    aws_session_token: str | None
    supports_effort: bool
    max_tokens: int
    # The mini model for this provider (mini runs on the same provider/credentials).
    mini_model: str


@lru_cache
def _catalog() -> Catalog:
    if not _CONFIG_PATH.exists():
        raise RuntimeError(f"{_CONFIG_PATH} not found — copy config.example.yaml to config.yaml")
    data = yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8")) or {}
    catalog = Catalog.model_validate(data)
    if not catalog.providers:
        raise RuntimeError("config.yaml defines no providers")
    logger.info("Loaded model catalog: %d providers", len(catalog.providers))
    return catalog


def list_models() -> ModelsResponse:
    """Every selectable model across all configured providers."""
    models = [
        ModelInfo(provider=pe.provider.value, provider_name=pe.name, model=me.id, supports_effort=me.effort)
        for pe in _catalog().providers
        for me in pe.models
    ]
    return ModelsResponse(models=models)


def resolve(provider: str | None = None, model: str | None = None) -> ResolvedModel:
    """Resolve a client selection to a concrete provider/model + credentials.

    Both None picks the catalog default (first provider's first model). An unknown
    provider or model raises ValidationError (422).
    """
    catalog = _catalog()
    if provider is None and model is None:
        default = catalog.providers[0]
        return _resolved(default, default.models[0])
    if provider is None:
        raise ValidationError("provider is required when selecting a model", details={"model": model})
    entry = next((p for p in catalog.providers if p.provider.value == provider), None)
    if entry is None:
        raise ValidationError(f"unknown provider {provider!r}", details={"provider": provider})
    chosen = next((m for m in entry.models if m.id == model), None) if model is not None else entry.models[0]
    if chosen is None:
        raise ValidationError(
            f"model {model!r} is not available for provider {provider!r}",
            details={"provider": provider, "model": model, "available": [m.id for m in entry.models]},
        )
    return _resolved(entry, chosen)


def _resolved(entry: ProviderEntry, model: ModelEntry) -> ResolvedModel:
    return ResolvedModel(
        provider=entry.provider,
        provider_name=entry.name,
        model=model.id,
        api_key=entry.api_key,
        base_url=entry.base_url,
        api_version=entry.api_version,
        region=entry.region,
        aws_access_key_id=entry.aws_access_key_id,
        aws_secret_access_key=entry.aws_secret_access_key,
        aws_session_token=entry.aws_session_token,
        supports_effort=model.effort,
        max_tokens=entry.max_tokens,
        mini_model=entry.mini_model,
    )
