import base64
import os
from contextlib import contextmanager

import psycopg2
from databricks.sdk import WorkspaceClient
from psycopg2.extras import RealDictCursor, Json


_w = WorkspaceClient()

_SCOPE = os.environ.get(
    "LAKEBASE_SECRET_SCOPE",
    "database",
)

_KEY = os.environ.get(
    "LAKEBASE_SECRET_KEY",
    "weather-lakebase-url",
)


def _lakebase_url() -> str:
    """
    Fetch the Lakebase PostgreSQL connection URL
    from a Databricks secret scope.
    """

    secret = _w.secrets.get_secret(
        scope=_SCOPE,
        key=_KEY,
    )

    return base64.b64decode(
        secret.value
    ).decode("utf-8")


@contextmanager
def get_connection():
    """
    Open a Lakebase PostgreSQL connection.

    RealDictCursor makes SELECT results behave
    like Python dictionaries.
    """

    conn = psycopg2.connect(
        _lakebase_url(),
        cursor_factory=RealDictCursor,
    )

    try:
        yield conn
    finally:
        conn.close()


def run_query(
    sql: str,
    params: tuple | dict | None = None,
) -> list[dict]:
    """
    Execute a SELECT query.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def run_write(
    sql: str,
    params: tuple | dict | None = None,
) -> int:
    """
    Execute one INSERT / UPDATE / DELETE statement.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            conn.commit()
            return cur.rowcount


def upsert_weather_documents(
    documents: list[dict],
) -> int:
    """
    Insert or update normalized weather documents.

    Duplicate document IDs are updated instead
    of creating duplicate rows.
    """

    if not documents:
        return 0

    sql = """
        INSERT INTO weather_documents (
            id,
            location,
            latitude,
            longitude,
            source_type,
            headline,
            narrative_text,
            issued_at,
            effective_at,
            payload,
            synced_at
        )
        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            now()
        )
        ON CONFLICT (id) DO UPDATE
        SET
            location = EXCLUDED.location,
            latitude = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude,
            source_type = EXCLUDED.source_type,
            headline = EXCLUDED.headline,
            narrative_text = EXCLUDED.narrative_text,
            issued_at = EXCLUDED.issued_at,
            effective_at = EXCLUDED.effective_at,
            payload = EXCLUDED.payload,
            synced_at = now()
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            for document in documents:
                cur.execute(
                    sql,
                    (
                        document["id"],
                        document["location"],
                        document.get("latitude"),
                        document.get("longitude"),
                        document["source_type"],
                        document.get("headline"),
                        document["narrative_text"],
                        document.get("issued_at"),
                        document.get("effective_at"),
                        Json(document["payload"]),
                    ),
                )

        conn.commit()

    return len(documents)

def upsert_weather_embedding(
    embedding_id: str,
    document_id: str,
    chunk_index: int,
    chunk_text: str,
    embedding: list[float],
    model_name: str,
) -> int:
    """
    Insert or update one weather embedding.
    """

    vector_string = (
        "["
        + ",".join(str(value) for value in embedding)
        + "]"
    )

    sql = """
        INSERT INTO weather_embeddings (
            id,
            document_id,
            chunk_index,
            chunk_text,
            embedding,
            model_name
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s::vector,
            %s
        )
        ON CONFLICT (document_id, chunk_index)
        DO UPDATE SET
            chunk_text = EXCLUDED.chunk_text,
            embedding = EXCLUDED.embedding,
            model_name = EXCLUDED.model_name,
            created_at = now()
    """

    return run_write(
        sql,
        (
            embedding_id,
            document_id,
            chunk_index,
            chunk_text,
            vector_string,
            model_name,
        ),
    )
def upsert_weather_embeddings(
    records: list[dict],
) -> int:
    """
    Insert or update multiple weather embeddings
    using one database connection.
    """

    if not records:
        return 0

    sql = """
        INSERT INTO weather_embeddings (
            id,
            document_id,
            chunk_index,
            chunk_text,
            embedding,
            model_name
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s::vector,
            %s
        )
        ON CONFLICT (document_id, chunk_index)
        DO UPDATE SET
            chunk_text = EXCLUDED.chunk_text,
            embedding = EXCLUDED.embedding,
            model_name = EXCLUDED.model_name,
            created_at = now()
    """

    with get_connection() as conn:
        with conn.cursor() as cur:

            for record in records:

                vector_string = (
                    "["
                    + ",".join(
                        str(value)
                        for value in record["embedding"]
                    )
                    + "]"
                )

                cur.execute(
                    sql,
                    (
                        record["id"],
                        record["document_id"],
                        record["chunk_index"],
                        record["chunk_text"],
                        vector_string,
                        record["model_name"],
                    ),
                )

        conn.commit()

    return len(records)

def search_weather_embeddings(
    query_embedding: list[float],
    limit: int = 5,
) -> list[dict]:
    """
    Find weather chunks most semantically similar
    to the supplied query embedding.
    """

    vector_string = (
        "["
        + ",".join(
            str(value)
            for value in query_embedding
        )
        + "]"
    )

    sql = """
        SELECT
            d.id AS document_id,
            d.location,
            d.source_type,
            d.headline,
            d.effective_at,
            e.chunk_index,
            e.chunk_text,
            1 - (
                e.embedding <=> %s::vector
            ) AS similarity
        FROM weather_embeddings e
        JOIN weather_documents d
            ON d.id = e.document_id
        ORDER BY
            e.embedding <=> %s::vector
        LIMIT %s
    """

    return run_query(
        sql,
        (
            vector_string,
            vector_string,
            limit,
        ),
    )


