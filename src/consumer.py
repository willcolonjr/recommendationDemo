"""Kafka consumer that enriches resort events and persists them to Postgres."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from contextlib import contextmanager
from dataclasses import dataclass
import psycopg
from kafka import KafkaConsumer
from sentence_transformers import SentenceTransformer
from rich.console import Console

from .config import get_settings

console = Console()
logger = logging.getLogger("consumer")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s - %(message)s")


@dataclass
class ResortRecord:
    id: str
    name: str
    location: str
    description: str
    amenities: list[str]
    themes: list[str]
    embedding: list[float]



def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{v:.8f}" for v in values) + "]"


class ResortRepository:
    def __init__(self, conn: psycopg.Connection, schema: str) -> None:
        self.conn = conn
        self.schema = schema

    def ensure_schema(self) -> None:
        ddl_path = Path(__file__).resolve().parent / "db" / "schema.sql"
        with ddl_path.open("r", encoding="utf-8") as ddl:
            self.conn.execute(f"SET search_path TO {self.schema}")
            self.conn.execute(ddl.read())
        self.conn.commit()

    def upsert(self, record: ResortRecord) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO {self.schema}.resorts (id, name, location, description, amenities, themes, embedding)
                VALUES (%(id)s, %(name)s, %(location)s, %(description)s, %(amenities)s, %(themes)s, %(embedding)s::vector)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    location = EXCLUDED.location,
                    description = EXCLUDED.description,
                    amenities = EXCLUDED.amenities,
                    themes = EXCLUDED.themes,
                    embedding = EXCLUDED.embedding;
                """,
                {
                    "id": record.id,
                    "name": record.name,
                    "location": record.location,
                    "description": record.description,
                    "amenities": record.amenities,
                    "themes": record.themes,
                    "embedding": _vector_literal(record.embedding),
                },
            )
        self.conn.commit()


@contextmanager
def _postgres_connection(settings):
    conn = psycopg.connect(
        host=settings.postgres.host,
        port=settings.postgres.port,
        dbname=settings.postgres.database,
        user=settings.postgres.user,
        password=settings.postgres.password,
        autocommit=False,
    )
    try:
        yield conn
    finally:
        conn.close()


class ResortEnricher:
    def __init__(self, model_name: str) -> None:
        self.model = SentenceTransformer(model_name)

    def transform(self, payload: dict[str, object]) -> ResortRecord:
        text_fields = [payload.get("name", ""), payload.get("description", "")]
        embedding = self.model.encode(". ".join(text_fields), normalize_embeddings=True)
        return ResortRecord(
            id=str(payload["id"]),
            name=str(payload.get("name", "")),
            location=str(payload.get("location", "")),
            description=str(payload.get("description", "")),
            amenities=[str(item) for item in payload.get("amenities", [])],
            themes=[str(item) for item in payload.get("themes", [])],
            embedding=embedding.tolist(),
        )


def main() -> None:
    settings = get_settings(kafka_client_id="resort-consumer")
    console.print(
        f"[bold blue]Starting consumer for topic {settings.kafka.topic} on {settings.kafka.broker}[/bold blue]"
    )

    consumer = KafkaConsumer(
        settings.kafka.topic,
        bootstrap_servers=settings.kafka.broker,
        client_id=settings.kafka.client_id,
        group_id="resort-consumers",
        value_deserializer=lambda payload: json.loads(payload.decode("utf-8")),
        key_deserializer=lambda payload: payload.decode("utf-8") if payload else None,
        enable_auto_commit=True,
        auto_offset_reset="earliest",
    )

    enricher = ResortEnricher(settings.embedding.model_name)

    with _postgres_connection(settings) as conn:
        repo = ResortRepository(conn, settings.postgres.schema)
        repo.ensure_schema()

        for message in consumer:
            record = enricher.transform(message.value)
            repo.upsert(record)
            console.log(f"Upserted resort {record.id}: {record.name}")


if __name__ == "__main__":
    main()
