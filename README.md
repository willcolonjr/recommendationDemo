# Timeshare Resort AI Recommender (Kafka + KRaft + Postgres)

This repository is a minimal, end-to-end implementation of an AI-powered
recommendation stack for timeshare resorts. It is inspired by the
[`timeshare-resort-ai-recommender`](https://github.com/paloknath/timeshare-resort-ai-recommender)
project, but swaps the infrastructure to use the open-source Apache Kafka
**KRaft** (KRaft = Kafka Raft) mode and Postgres enhanced with vector and natural
language search extensions.

The stack showcases how to ingest resort listing events, enrich them with text
embeddings, persist the data in Postgres using [`pgvector`](https://github.com/pgvector/pgvector),
and expose a simple similarity search API.

## Architecture Overview

```
┌──────────┐   Resort listings   ┌─────────────┐   Enriched records   ┌────────────┐
│ producer │ ───────────────────▶│ Kafka topic │─────────────────────▶│ consumer & │
│ (Python) │                     │    resorts  │                      │ Postgres   │
└──────────┘                     └─────────────┘                      └────────────┘
                                                     │
                                                     ▼
                                        Vector + text similarity queries
```

* **Producer** – Streams resort inventory events to Kafka.
* **Kafka (KRaft)** – A single-node Kafka cluster running in KRaft mode (no
  ZooKeeper) managed via Docker Compose.
* **Consumer / Enricher** – Consumes events, generates text embeddings using
  `sentence-transformers`, and upserts records into Postgres.
* **Postgres** – Stores structured resort data, vector embeddings
  (`pgvector`), and enables trigram-based natural language search (`pg_trgm`).
* **FastAPI API** – Provides REST endpoints for collecting preferences and returning ranked resorts.
* **React Frontend** – Offers an interactive planner that calls the API.

## Getting Started

### Prerequisites

* Docker & Docker Compose v2
* Python 3.10+

### 1. Configure environment variables

Copy `.env.example` to `.env` and adjust values as needed:

```bash
cp .env.example .env
```

### 2. Start infrastructure

```bash
docker compose up -d
```

This command launches:

* `kafka` – Apache Kafka 3.5 in KRaft mode with the `resorts` topic
  bootstrapped automatically.
* `postgres` – Postgres 16 with `pgvector` and `pg_trgm` extensions enabled.

### 3. Install Python dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Seed sample data

```bash
python src/producer.py --seed-data ./data/resorts.jsonl
```

This publishes resort events into Kafka.

### 5. Run the consumer

```bash
python src/consumer.py
```

The consumer will:

1. Ensure database schema and extensions exist.
2. Generate embeddings for the resort description/name fields.
3. Upsert the records into Postgres.

### 6. Start the API

```bash
uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
```

The FastAPI service exposes REST endpoints for the UI at `http://localhost:8000/api`.

### 7. Query recommendations

Use the simple CLI to search for similar resorts:

```bash
python src/recommender.py --query "family friendly beach resort"
```

### 8. Launch the web frontend

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173` to try the interactive planner UI. The Vite dev server proxies API requests to `localhost:8000`.

## API Reference

### `GET /api/health`

Returns `{ "status": "ok" }` so the frontend (and monitors) can verify that the service is online.

### `POST /api/recommendations`

Request body:

```json
{
  "query": "Looking for a family friendly beach resort",
  "k": 5,
  "use_vector": true
}
```

Response body:

```json
{
  "results": [
    {
      "id": "WYN-MAUI-001",
      "name": "Club Wyndham Ka Eo Kai",
      "location": "Kauai, Hawaii",
      "description": "Spacious villas with ocean views and a sprawling pool complex perfect for families.",
      "score": 0.8421,
      "weight": 1.0,
      "strategy": "vector_similarity",
      "info": "Cosine similarity over pgvector embeddings"
    }
  ]
}
```

* **score** – the raw similarity value returned by Postgres.
* **weight** – the normalized weight (0–1) of the resort relative to the other results in the payload.
* **strategy** – `vector_similarity` (pgvector cosine) or `text_similarity` (Postgres trigram).
* **info** – a human-readable explanation the frontend can surface alongside the resort.

The React UI now displays both the raw score and the normalized weight for each resort, along with the scoring strategy.
## Project Structure

```
├── docker-compose.yml        # Kafka (KRaft) + Postgres with extensions
├── requirements.txt          # Python runtime dependencies
├── src/
│   ├── api.py                # FastAPI service powering the frontend
│   ├── config.py             # Shared configuration loader
│   ├── consumer.py           # Kafka consumer & Postgres writer
│   ├── producer.py           # Demo Kafka producer
│   ├── recommender.py        # CLI for similarity + text search queries
│   ├── recommendations.py    # Shared recommendation query helpers
│   └── db/
│       └── schema.sql        # Database DDL & extension setup
├── frontend/                 # React + Vite single-page application
│   └── src/                  # UI components & styling assets
├── data/
│   └── resorts.jsonl         # Sample dataset
└── README.md
```

## Extending the Project

* Swap the `sentence-transformers` model in `consumer.py` or the API for a
  domain-specific embedding model.
* Containerize the FastAPI service and frontend together for one-command
  deployment.
* Introduce streaming analytics with Kafka Streams or ksqlDB.

## License

This project is provided under the MIT License. See [LICENSE](LICENSE) for
details.

