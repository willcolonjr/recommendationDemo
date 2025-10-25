"""FastAPI application that exposes resort recommendation endpoints."""

from __future__ import annotations

from dataclasses import asdict
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

from .config import Settings, get_settings
from .recommendations import fetch_recommendations

app = FastAPI(title="Resort Recommender API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RecommendationRequest(BaseModel):
    query: str = Field(..., description="Free-text description of desired resort features.")
    k: int = Field(5, ge=1, le=20, description="Number of results to return.")
    use_vector: bool = Field(True, description="Toggle between vector similarity and trigram search.")
    model_id: str | None = Field(
        None,
        description="Identifier for the embedding model to use when vector search is enabled.",
    )


class ResortResponse(BaseModel):
    id: str
    name: str
    location: str
    description: str
    score: float = Field(..., description="Raw similarity score returned by Postgres.")
    weight: float = Field(..., description="Normalized weight based on the result list.")
    strategy: str = Field(..., description="Similarity strategy used for the ranking.")
    info: str = Field(..., description="Human-readable explanation of how the score was produced.")


class RecommendationResponse(BaseModel):
    model_id: str | None = Field(None, description="Embedding model identifier used for scoring.")
    model_name: str | None = Field(None, description="Human-readable name of the embedding model.")
    results: list[ResortResponse]


def get_settings_dependency() -> Settings:
    return get_settings()


@lru_cache(maxsize=8)
def _load_model(model_name: str) -> SentenceTransformer:
    """Cache and return a ``SentenceTransformer`` instance by name."""

    return SentenceTransformer(model_name)


@app.get("/api/health", tags=["meta"])
def healthcheck() -> dict[str, str]:
    """Basic health endpoint used by the frontend."""

    return {"status": "ok"}


class EmbeddingModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    description: str


class EmbeddingModelListResponse(BaseModel):
    default_model_id: str
    models: list[EmbeddingModelInfo]


@app.get("/api/models", response_model=EmbeddingModelListResponse, tags=["recommendations"])
def list_embedding_models(
    settings: Annotated[Settings, Depends(get_settings_dependency)],
) -> EmbeddingModelListResponse:
    """Return metadata about the available embedding models for Flint flows."""

    models = [
        EmbeddingModelInfo(
            id=model.id,
            name=model.name,
            provider=model.provider,
            description=model.description,
        )
        for model in settings.embedding.available()
    ]
    return EmbeddingModelListResponse(
        default_model_id=settings.embedding.default_model_id,
        models=models,
    )


@app.post("/api/recommendations", response_model=RecommendationResponse, tags=["recommendations"])
def create_recommendations(
    payload: RecommendationRequest,
    settings: Annotated[Settings, Depends(get_settings_dependency)],
) -> RecommendationResponse:
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty.")

    resolved_model = None
    resolved_model_info = None
    if payload.use_vector:
        try:
            resolved_model_info = settings.embedding.resolve(payload.model_id)
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        resolved_model = _load_model(resolved_model_info.model)

    rows = fetch_recommendations(
        query=payload.query,
        k=payload.k,
        use_vector=payload.use_vector,
        model=resolved_model if payload.use_vector else None,
        settings=settings,
    )

    if not rows:
        return RecommendationResponse(
            model_id=resolved_model_info.id if resolved_model_info else None,
            model_name=resolved_model_info.name if resolved_model_info else None,
            results=[],
        )

    max_score = max(row.score for row in rows)
    min_score = min(row.score for row in rows)
    denominator = max_score - min_score

    def _normalized(score: float) -> float:
        if denominator == 0:
            return 1.0 if score != 0 else 0.0
        return (score - min_score) / denominator

    return RecommendationResponse(
        model_id=resolved_model_info.id if resolved_model_info else None,
        model_name=resolved_model_info.name if resolved_model_info else None,
        results=[
            ResortResponse(**asdict(row), weight=_normalized(row.score))
            for row in rows
        ],
    )
