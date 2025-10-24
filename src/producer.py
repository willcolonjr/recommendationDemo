"""Kafka producer that publishes resort events from a JSONL file."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterator

import click
from kafka import KafkaProducer
from rich.console import Console
from rich.progress import Progress

from .config import get_settings

console = Console()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s - %(message)s")
logger = logging.getLogger("producer")


@click.command()
@click.option(
    "--seed-data",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to a JSONL file of resort events.",
)
@click.option("--bootstrap", is_flag=True, help="Create the Kafka topic if needed.")
def main(seed_data: Path, bootstrap: bool) -> None:
    """Publish resort events to Kafka."""
    settings = get_settings(kafka_client_id="resort-producer")
    producer = KafkaProducer(
        bootstrap_servers=settings.kafka.broker,
        client_id=settings.kafka.client_id,
        value_serializer=lambda payload: json.dumps(payload).encode("utf-8"),
        key_serializer=lambda payload: payload.encode("utf-8"),
    )

    try:
        events = list(_load_events(seed_data))
        if not events:
            console.print("[yellow]No events found to publish.[/yellow]")
            return

        if bootstrap:
            _ensure_topic(settings.kafka.broker, settings.kafka.topic)

        console.print(
            f"[bold green]Publishing {len(events)} events to topic {settings.kafka.topic}[/bold green]"
        )

        with Progress() as progress:
            task = progress.add_task("Publishing", total=len(events))
            for event in events:
                producer.send(
                    settings.kafka.topic,
                    key=event["id"],
                    value=event,
                )
                progress.advance(task)
        producer.flush()
    finally:
        producer.close()


def _load_events(path: Path) -> Iterator[dict[str, object]]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def _ensure_topic(bootstrap_server: str, topic: str) -> None:
    from kafka.admin import KafkaAdminClient, NewTopic
    from kafka.errors import TopicAlreadyExistsError

    admin = KafkaAdminClient(bootstrap_servers=bootstrap_server)
    try:
        admin.create_topics([NewTopic(name=topic, num_partitions=3, replication_factor=1)])
        logger.info("Created topic %s", topic)
    except TopicAlreadyExistsError:
        logger.info("Topic %s already exists", topic)
    finally:
        admin.close()


if __name__ == "__main__":
    main()
