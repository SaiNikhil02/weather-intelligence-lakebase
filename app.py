from flask import Flask, jsonify, request

import lakebase
from weather_client import WeatherClient
from weather_embeddings import generate_embedding


app = Flask(__name__)

weather_client = WeatherClient()


@app.get("/healthz")
def healthz():
    return jsonify({"status": "ok"}), 200


@app.post("/weather/sync")
def weather_sync():
    body = request.get_json(silent=True) or {}

    location = body.get("location")
    latitude = body.get("latitude")
    longitude = body.get("longitude")

    if (
        not location
        or latitude is None
        or longitude is None
    ):
        return jsonify(
            {
                "error": (
                    "location, latitude and longitude "
                    "are required"
                )
            }
        ), 400

    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError):
        return jsonify(
            {
                "error": (
                    "latitude and longitude "
                    "must be numbers"
                )
            }
        ), 400

    forecasts = weather_client.get_forecast(
        latitude,
        longitude,
    )

    alerts = weather_client.get_alerts(
        latitude,
        longitude,
    )

    forecast_documents = (
        weather_client.normalize_forecasts(
            location,
            latitude,
            longitude,
            forecasts,
        )
    )

    alert_documents = (
        weather_client.normalize_alerts(
            location,
            latitude,
            longitude,
            alerts,
        )
    )

    documents = (
        forecast_documents
        + alert_documents
    )

    processed = (
        lakebase.upsert_weather_documents(
            documents
        )
    )

    return jsonify(
        {
            "location": location,
            "forecast_documents": len(
                forecast_documents
            ),
            "alert_documents": len(
                alert_documents
            ),
            "processed_documents": processed,
        }
    ), 200

@app.post("/weather/search")
def weather_search():
    body = request.get_json(silent=True) or {}

    query = (
        body.get("query") or ""
    ).strip()

    if not query:
        return jsonify(
            {
                "error": "query is required"
            }
        ), 400

    try:
        top_k = int(
            body.get("top_k", 5)
        )
    except (TypeError, ValueError):
        return jsonify(
            {
                "error": "top_k must be an integer"
            }
        ), 400

    top_k = max(
        1,
        min(top_k, 20),
    )

    query_embedding = generate_embedding(
        query
    )

    results = (
        lakebase.search_weather_embeddings(
            query_embedding,
            limit=top_k,
        )
    )

    response_results = []

    for row in results:
        response_results.append(
            {
                "document_id": row["document_id"],
                "location": row["location"],
                "source_type": row["source_type"],
                "headline": row["headline"],
                "effective_at": (
                    row["effective_at"].isoformat()
                    if row["effective_at"]
                    else None
                ),
                "chunk_index": row["chunk_index"],
                "text": row["chunk_text"],
                "similarity": float(
                    row["similarity"]
                ),
            }
        )

    return jsonify(
        {
            "query": query,
            "count": len(response_results),
            "results": response_results,
        }
    ), 200