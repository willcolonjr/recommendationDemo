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

### Quick start with Docker

1. Copy the environment template and adjust values as needed:

   ```bash
   cp .env.example .env
   ```

2. Start Kafka and Postgres in the background:

   ```bash
   docker compose up -d
   # or: make up
   ```

3. Tail logs while developing:

   ```bash
   docker compose logs -f
   # or: make logs
   ```

4. Shut everything down when you are done:

   ```bash
   docker compose down -v
   # or: make down
   ```

### 1. Configure environment variables

Copy `.env.example` to `.env` and adjust values as needed:

```bash
cp .env.example .env
```

Key environment variables for the embedding pipeline:

| Variable | Description | Default |
| --- | --- | --- |
| `EMBEDDING_MODEL` | Default embedding model identifier used by the consumer/API. Must exist in the registry. | `sentence-transformers/all-MiniLM-L6-v2` |
| `EMBEDDING_MODEL_REGISTRY` | Optional JSON array/object describing the available embedding models. Each entry should include `id`, `model`, `name`, `provider`, and `description`. When omitted, a MiniLM and an E5 model are registered automatically. | *(built-in registry)* |

### 2. Start infrastructure

`docker compose up -d` (or `make up`) launches:

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

### `GET /api/models`

Returns the registry of embedding models that the Flint planning flows can swap between. Sample response:

```json
{
  "default_model_id": "sentence-transformers/all-MiniLM-L6-v2",
  "models": [
    {
      "id": "sentence-transformers/all-MiniLM-L6-v2",
      "name": "all-MiniLM-L6-v2",
      "provider": "SentenceTransformers",
      "description": "Balanced general-purpose MiniLM embeddings (384 dims)."
    },
    {
      "id": "intfloat/e5-base-v2",
      "name": "E5 Base v2",
      "provider": "Intfloat",
      "description": "Stronger semantic search embeddings with higher dimensionality (768 dims)."
    }
  ]
}
```

The frontend consumes this endpoint to show a drop-down for selecting the active embedding model. Requests to `/api/recommendations` can include an optional `model_id` to override the default.
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

