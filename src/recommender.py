"""CLI utility for running similarity and natural language searches."""

from __future__ import annotations

import json
import logging

import click
from rich.console import Console
from rich.table import Table
from sentence_transformers import SentenceTransformer

from .config import get_settings
from .recommendations import ResortRow, fetch_recommendations

console = Console()
logger = logging.getLogger("recommender")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s - %(message)s")


@click.command()
@click.option("--query", required=True, help="Free-text description of what the guest wants.")
@click.option("--k", default=3, show_default=True, help="Number of recommendations to fetch.")
@click.option("--similarity", is_flag=True, help="Use vector similarity search.")
@click.option(
    "--raw", is_flag=True, help="Print the raw JSON rows returned by Postgres instead of a table."
)
def main(query: str, k: int, similarity: bool, raw: bool) -> None:
    """Fetch resort recommendations from Postgres."""
    settings = get_settings()
    model = None

    if similarity:
        model = SentenceTransformer(settings.embedding.model_name)

    rows = fetch_recommendations(
        query=query,
        k=k,
        use_vector=similarity,
        model=model,
        settings=settings,
    )

    if not rows:
        console.print("[yellow]No resorts matched the query.[/yellow]")
        return

    if raw:
        console.print_json(json.dumps([row.__dict__ for row in rows], indent=2))
        return

    _print_table(rows)


def _print_table(rows: list[ResortRow]) -> None:
    table = Table(title="Resort Recommendations", show_lines=True)
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="bold")
    table.add_column("Location")
    table.add_column("Description")
    table.add_column("Strategy")
    table.add_column("Score", justify="right")
    table.add_column("Weight", justify="right")

    max_score = max(row.score for row in rows)
    min_score = min(row.score for row in rows)
    denominator = max_score - min_score

    def _normalized(score: float) -> float:
        if denominator == 0:
            return 1.0 if score != 0 else 0.0
        return (score - min_score) / denominator

    for row in rows:
        table.add_row(
            row.id,
            row.name,
            row.location,
            row.description,
            row.strategy,
            f"{row.score:.4f}",
            f"{_normalized(row.score):.4f}",
        )

    console.print(table)


if __name__ == "__main__":
    main()
