"""Shared configuration utilities for the recommender stack."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

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
class EmbeddingSettings:
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"


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

    embedding = EmbeddingSettings(
        model_name=_env(
            "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        )
    )

    return Settings(kafka=kafka, postgres=postgres, embedding=embedding)


def _env(key: str, default: str) -> str:
    value = os.getenv(key)
    return value if value is not None else default


import os  # noqa: E402  (import after function definitions for mypy friendliness)
