# Weather Intelligence

Weather Intelligence is a Databricks + Lakebase application that ingests
unstructured weather data from the National Weather Service API, stores the
raw documents in Lakebase PostgreSQL, generates semantic embeddings using
Sentence Transformers, and performs vector similarity search using pgvector.

## Architecture

NWS API
→ Weather Client
→ Normalized Weather Documents
→ Lakebase
→ Text Chunking
→ MiniLM Embeddings
→ pgvector
→ Flask REST API
→ Semantic Weather Search

## Technologies

- Databricks
- Lakebase PostgreSQL
- pgvector
- Flask
- psycopg2
- National Weather Service API
- sentence-transformers/all-MiniLM-L6-v2
- Python

## Database Tables

### weather_documents

Stores normalized weather forecasts and alerts.

Important fields:

- `id`
- `location`
- `latitude`
- `longitude`
- `source_type`
- `headline`
- `narrative_text`
- `issued_at`
- `effective_at`
- `payload`

### weather_embeddings

Stores chunks and their semantic embeddings.

Important fields:

- `id`
- `document_id`
- `chunk_index`
- `chunk_text`
- `embedding VECTOR(384)`
- `model_name`

A foreign key connects each embedding back to its source weather document.

## Weather Data Source

The application uses the public National Weather Service API.

No API key is required.

Example flow:

1. Latitude and longitude are sent to `/points/{lat},{lon}`.
2. NWS returns the forecast endpoint for that location.
3. Forecast periods are retrieved.
4. Active weather alerts are retrieved for the coordinate.
5. The responses are normalized before being stored in Lakebase.

## Sync API

### POST /weather/sync

Example request:
```json
{
  "location": "Chicago, IL",
  "latitude": 41.8781,
  "longitude": -87.6298
}
```

The application uses deterministic document IDs and PostgreSQL UPSERT logic
to avoid creating duplicate records when the same forecast is synchronized
multiple times.

Embeddings

Weather narratives are split into chunks of up to 800 characters with a
100-character overlap.

Each chunk is embedded using:

sentence-transformers/all-MiniLM-L6-v2

The model produces a 384-dimensional embedding, which is stored in:

VECTOR(384)

Semantic Search API
POST /weather/search

Example request:

{
  "query": "heavy rain and flash flooding",
  "top_k": 5
}

The query is converted into the same 384-dimensional embedding space.

Lakebase pgvector compares the query vector against stored weather vectors
using cosine distance:

embedding <=> query_vector

Similarity is calculated as:

1 - (embedding <=> query_vector)

The most semantically relevant weather chunks are returned first.

Example Search Result

A search for:

heavy rain and flash flooding

returned weather forecasts related to:

thunderstorms
1–2 inches of rainfall
high precipitation probability
rain showers

This demonstrates semantic retrieval rather than simple keyword matching.

API Validation

The API validates invalid requests.

Missing query:

{
  "error": "query is required"
}

Invalid top_k:

{
  "error": "top_k must be an integer"
}

Both return HTTP status 400.

Project Structure
weather-intelligence-lakebase/
├── app.py
├── lakebase.py
├── weather_client.py
├── weather_embeddings.py
├── README_WEATHER.md
└── notebooks/
    └── test_pipeline
Security

The Lakebase connection URL is not stored in source code.

It is stored in a Databricks Secret Scope and retrieved at runtime.

Secret:

database/weather-lakebase-url

Key Concepts Demonstrated
Unstructured API data ingestion
PostgreSQL UPSERT / idempotent pipelines
JSONB storage
Foreign-key integrity
Text chunking
Sentence embeddings
pgvector
HNSW vector indexing
Cosine similarity
Semantic retrieval
Flask REST APIs
