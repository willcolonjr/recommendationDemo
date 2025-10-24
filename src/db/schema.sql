CREATE TABLE IF NOT EXISTS resorts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    location TEXT NOT NULL,
    description TEXT,
    amenities TEXT[],
    themes TEXT[],
    embedding vector(384)
);

CREATE INDEX IF NOT EXISTS resorts_embedding_idx
    ON resorts
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS resorts_description_trgm_idx
    ON resorts
    USING gin (description gin_trgm_ops);

CREATE INDEX IF NOT EXISTS resorts_name_trgm_idx
    ON resorts
    USING gin (name gin_trgm_ops);
