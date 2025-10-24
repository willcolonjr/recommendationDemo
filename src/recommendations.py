"""Shared recommendation query utilities for CLI and API surfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import psycopg
from sentence_transformers import SentenceTransformer

from .config import Settings, get_settings


@dataclass
class ResortRow:
    """A projected resort row returned from the database."""

    id: str
    name: str
    location: str
    description: str
    score: float
    strategy: str
    info: str


_SETTINGS = get_settings()


def get_default_settings() -> Settings:
    """Return the cached global settings instance."""

    return _SETTINGS


def _vector_literal(values: Sequence[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"


def _similarity_sql(k: int) -> str:
    return f"""
        SELECT id, name, location, description,
               1 - (embedding <=> %(query_vector)s::vector) AS score
        FROM resorts
        ORDER BY embedding <=> %(query_vector)s::vector
        LIMIT {k};
    """


def _text_search_sql(k: int) -> str:
    return f"""
        SELECT id, name, location, description,
               similarity(description, %(query)s) AS score
        FROM resorts
        ORDER BY score DESC
        LIMIT {k};
    """


def fetch_recommendations(
    *,
    query: str,
    k: int,
    use_vector: bool,
    model: SentenceTransformer | None,
    settings: Settings | None = None,
) -> list[ResortRow]:
    """Return the top ``k`` resorts for ``query`` using similarity or text search."""

    config = settings or _SETTINGS
    params: dict[str, object]

    if use_vector:
        if model is None:
            raise ValueError("A sentence-transformer model must be provided for vector search.")
        query_vector = model.encode(query, normalize_embeddings=True).tolist()
        sql = _similarity_sql(k)
        params = {"query_vector": _vector_literal(query_vector)}
        strategy = "vector_similarity"
        info = "Cosine similarity over pgvector embeddings"
    else:
        sql = _text_search_sql(k)
        params = {"query": query}
        strategy = "text_similarity"
        info = "Trigram similarity over resort descriptions"

    with psycopg.connect(
        host=config.postgres.host,
        port=config.postgres.port,
        dbname=config.postgres.database,
        user=config.postgres.user,
        password=config.postgres.password,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = [
                ResortRow(
                    id=row[0],
                    name=row[1],
                    location=row[2],
                    description=row[3],
                    score=row[4],
                    strategy=strategy,
                    info=info,
                )
                for row in cur.fetchall()
            ]

    return rows


__all__ = [
    "ResortRow",
    "fetch_recommendations",
    "get_default_settings",
]
