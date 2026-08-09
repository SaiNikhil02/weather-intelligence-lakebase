-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;


-- =====================================================
-- Raw / normalized weather documents
-- =====================================================

CREATE TABLE IF NOT EXISTS weather_documents (
    id TEXT PRIMARY KEY,

    location TEXT NOT NULL,

    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,

    source_type TEXT NOT NULL,

    headline TEXT,

    narrative_text TEXT NOT NULL,

    issued_at TIMESTAMPTZ,
    effective_at TIMESTAMPTZ,

    payload JSONB NOT NULL,

    synced_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT valid_weather_source_type
        CHECK (
            source_type IN (
                'alert',
                'forecast'
            )
        )
);


CREATE INDEX IF NOT EXISTS idx_weather_documents_location
ON weather_documents (location);


CREATE INDEX IF NOT EXISTS idx_weather_documents_source_type
ON weather_documents (source_type);


-- =====================================================
-- Weather vector embeddings
-- =====================================================

CREATE TABLE IF NOT EXISTS weather_embeddings (
    id TEXT PRIMARY KEY,

    document_id TEXT NOT NULL,

    chunk_index INTEGER NOT NULL,

    chunk_text TEXT NOT NULL,

    embedding VECTOR(384) NOT NULL,

    model_name TEXT NOT NULL
        DEFAULT 'sentence-transformers/all-MiniLM-L6-v2',

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_weather_embedding_document
        FOREIGN KEY (document_id)
        REFERENCES weather_documents(id)
        ON DELETE CASCADE,

    CONSTRAINT unique_weather_document_chunk
        UNIQUE (
            document_id,
            chunk_index
        )
);


CREATE INDEX IF NOT EXISTS idx_weather_embeddings_document_id
ON weather_embeddings (document_id);


-- HNSW index for cosine similarity search
CREATE INDEX IF NOT EXISTS idx_weather_embeddings_vector
ON weather_embeddings
USING hnsw (
    embedding vector_cosine_ops
);
