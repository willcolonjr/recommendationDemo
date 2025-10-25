"""Shared configuration utilities for the recommender stack."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

from dotenv import load_dotenv

# Load environment variables from .env if present.
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env", override=False)


@dataclass(frozen=True)
class KafkaSettings:
    broker: str = "localhost:9092"
    topic: str = "resorts"
    client_id: str = "resort-producer"


@dataclass(frozen=True)
class PostgresSettings:
    host: str = "localhost"
    port: int = 5432
    database: str = "resorts"
    user: str = "resorts"
    password: str = "resorts"
    schema: str = "public"


@dataclass(frozen=True)
class EmbeddingModelConfig:
    """Describe an embedding model available to the application."""

    id: str
    name: str
    provider: str
    description: str
    model: str


@dataclass(frozen=True)
class EmbeddingSettings:
    default_model_id: str
    models: Mapping[str, EmbeddingModelConfig]

    def resolve(self, model_id: Optional[str] = None) -> EmbeddingModelConfig:
        target = model_id or self.default_model_id
        try:
            return self.models[target]
        except KeyError as exc:
            raise KeyError(f"Unknown embedding model '{target}'.") from exc

    def available(self) -> tuple[EmbeddingModelConfig, ...]:
        return tuple(self.models.values())


@dataclass(frozen=True)
class Settings:
    kafka: KafkaSettings
    postgres: PostgresSettings
    embedding: EmbeddingSettings


def get_settings(
    *,
    kafka_client_id: Optional[str] = None,
    kafka_topic: Optional[str] = None,
) -> Settings:
    """Load settings from environment variables."""

    kafka = KafkaSettings(
        broker=_env("KAFKA_BROKER", "localhost:9092"),
        topic=kafka_topic or _env("KAFKA_TOPIC", "resorts"),
        client_id=kafka_client_id or _env("KAFKA_CLIENT_ID", "resort-service"),
    )

    postgres = PostgresSettings(
        host=_env("POSTGRES_HOST", "localhost"),
        port=int(_env("POSTGRES_PORT", "5432")),
        database=_env("POSTGRES_DB", "resorts"),
        user=_env("POSTGRES_USER", "resorts"),
        password=_env("POSTGRES_PASSWORD", "resorts"),
        schema=_env("POSTGRES_SCHEMA", "public"),
    )

    embedding_models = _load_embedding_models(
        _env("EMBEDDING_MODEL_REGISTRY", "")
    )
    default_model_id = _env("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    if default_model_id not in embedding_models:
        default_model_id = next(iter(embedding_models))

    embedding = EmbeddingSettings(
        default_model_id=default_model_id,
        models=embedding_models,
    )

    return Settings(kafka=kafka, postgres=postgres, embedding=embedding)


def _env(key: str, default: str) -> str:
    value = os.getenv(key)
    return value if value is not None else default


import os  # noqa: E402  (import after function definitions for mypy friendliness)


def _load_embedding_models(raw_registry: str) -> dict[str, EmbeddingModelConfig]:
    """Parse a registry of embedding models from JSON or use defaults."""

    defaults = {
        cfg.id: cfg
        for cfg in (
            EmbeddingModelConfig(
                id="sentence-transformers/all-MiniLM-L6-v2",
                name="all-MiniLM-L6-v2",
                provider="SentenceTransformers",
                description="Balanced general-purpose MiniLM embeddings (384 dims).",
                model="sentence-transformers/all-MiniLM-L6-v2",
            ),
            EmbeddingModelConfig(
                id="intfloat/e5-base-v2",
                name="E5 Base v2",
                provider="Intfloat",
                description="Stronger semantic search embeddings with higher dimensionality (768 dims).",
                model="intfloat/e5-base-v2",
            ),
        )
    }

    if not raw_registry.strip():
        return defaults

    try:
        import json

        parsed = json.loads(raw_registry)
    except Exception:
        return defaults

    registry: dict[str, EmbeddingModelConfig] = {}
    if isinstance(parsed, list):
        entries = parsed
    elif isinstance(parsed, dict):
        entries = parsed.values()
    else:
        entries = []

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        model_id = str(entry.get("id", "")).strip()
        model_name = str(entry.get("model", "")).strip()
        if not model_id or not model_name:
            continue
        registry[model_id] = EmbeddingModelConfig(
            id=model_id,
            name=str(entry.get("name") or model_id),
            provider=str(entry.get("provider") or "custom"),
            description=str(entry.get("description") or ""),
            model=model_name,
        )

    return registry or defaults
