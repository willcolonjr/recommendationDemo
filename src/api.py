"""FastAPI application that exposes resort recommendation endpoints."""

from __future__ import annotations

from dataclasses import asdict
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
    results: list[ResortResponse]


def get_settings_dependency() -> Settings:
    return get_settings()


def get_model_dependency(settings: Annotated[Settings, Depends(get_settings_dependency)]) -> SentenceTransformer:
    model_name = settings.embedding.model_name
    if not hasattr(get_model_dependency, "_model"):
        get_model_dependency._model = SentenceTransformer(model_name)  # type: ignore[attr-defined]
    return get_model_dependency._model  # type: ignore[attr-defined]


@app.get("/api/health", tags=["meta"])
def healthcheck() -> dict[str, str]:
    """Basic health endpoint used by the frontend."""

    return {"status": "ok"}


@app.post("/api/recommendations", response_model=RecommendationResponse, tags=["recommendations"])
def create_recommendations(
    payload: RecommendationRequest,
    settings: Annotated[Settings, Depends(get_settings_dependency)],
    model: Annotated[SentenceTransformer, Depends(get_model_dependency)],
) -> RecommendationResponse:
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty.")

    rows = fetch_recommendations(
        query=payload.query,
        k=payload.k,
        use_vector=payload.use_vector,
        model=model if payload.use_vector else None,
        settings=settings,
    )

    if not rows:
        return RecommendationResponse(results=[])

    max_score = max(row.score for row in rows)
    min_score = min(row.score for row in rows)
    denominator = max_score - min_score

    def _normalized(score: float) -> float:
        if denominator == 0:
            return 1.0 if score != 0 else 0.0
        return (score - min_score) / denominator

    return RecommendationResponse(
        results=[
            ResortResponse(**asdict(row), weight=_normalized(row.score))
            for row in rows
        ]
    )
