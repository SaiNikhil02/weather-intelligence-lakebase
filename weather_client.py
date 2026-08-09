import requests
import hashlib
import json


class WeatherClient:
    """
    Small client for the National Weather Service API.

    No API key is required.
    """

    def __init__(
        self,
        base_url: str = "https://api.weather.gov",
        timeout: int = 30,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        self.session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent": (
                    "weather-intelligence-databricks-app "
                    "(contact: sainikhil123.sb@gmail.com)"
                ),
                "Accept": "application/geo+json",
            }
        )

    def _get(self, url: str, params: dict | None = None) -> dict:
        response = self.session.get(
            url,
            params=params,
            timeout=self.timeout,
        )

        response.raise_for_status()

        return response.json()

    def get_point_metadata(
        self,
        latitude: float,
        longitude: float,
    ) -> dict:
        """
        Resolve latitude/longitude into NWS grid metadata.

        The response contains URLs such as:
        - forecast
        - forecastHourly
        """

        url = (
            f"{self.base_url}/points/"
            f"{latitude},{longitude}"
        )

        return self._get(url)

    def get_forecast(
        self,
        latitude: float,
        longitude: float,
    ) -> list[dict]:
        """
        Fetch the multi-day forecast for a location.
        """

        point_data = self.get_point_metadata(
            latitude,
            longitude,
        )

        forecast_url = (
            point_data
            .get("properties", {})
            .get("forecast")
        )

        if not forecast_url:
            return []

        forecast_data = self._get(forecast_url)

        return (
            forecast_data
            .get("properties", {})
            .get("periods", [])
        )

    def get_alerts(
        self,
        latitude: float,
        longitude: float,
    ) -> list[dict]:
        """
        Fetch active weather alerts for a point.
        """

        url = f"{self.base_url}/alerts/active"

        data = self._get(
            url,
            params={
                "point": f"{latitude},{longitude}"
            },
        )

        return data.get("features", [])
    

    def normalize_forecasts(
    self,
    location: str,
    latitude: float,
    longitude: float,
    periods: list[dict],
) -> list[dict]:
    
        documents = []

        for period in periods:
            narrative_text = (
                period.get("detailedForecast") or ""
            ).strip()

            if not narrative_text:
                continue

            start_time = period.get("startTime")
            period_name = period.get("name", "Forecast")

            # Forecast periods don't provide a simple stable document ID,
            # so create one deterministically from location + period time.
            raw_key = (
                f"forecast|{location}|"
                f"{start_time}|{period_name}"
            )

            document_hash = hashlib.sha256(
                raw_key.encode("utf-8")
            ).hexdigest()

            document_id = f"forecast_{document_hash[:32]}"

            documents.append(
                {
                    "id": document_id,
                    "location": location,
                    "latitude": latitude,
                    "longitude": longitude,
                    "source_type": "forecast",
                    "headline": period_name,
                    "narrative_text": narrative_text,
                    "issued_at": None,
                    "effective_at": start_time,
                    "payload": period,
                }
            )

        return documents
    


    def normalize_alerts(
    self,
    location: str,
    latitude: float,
    longitude: float,
    alerts: list[dict],
) -> list[dict]:
        """
        Convert NWS alerts into our weather_documents schema.
        """

        documents = []

        for alert in alerts:
            properties = alert.get("properties", {})

            description = (
                properties.get("description") or ""
            ).strip()

            instruction = (
                properties.get("instruction") or ""
            ).strip()

            narrative_parts = []

            if description:
                narrative_parts.append(description)

            if instruction:
                narrative_parts.append(
                    f"Instructions: {instruction}"
                )

            narrative_text = "\n\n".join(
                narrative_parts
            )

            if not narrative_text:
                continue

            # NWS alerts normally provide a stable feature ID.
            alert_id = alert.get("id")

            if alert_id:
                document_id = alert_id
            else:
                fallback_key = (
                    f"alert|{location}|"
                    f"{properties.get('event')}|"
                    f"{properties.get('sent')}"
                )

                alert_hash = hashlib.sha256(
                    fallback_key.encode("utf-8")
                ).hexdigest()

                document_id = f"alert_{alert_hash[:32]}"

            documents.append(
                {
                    "id": document_id,
                    "location": location,
                    "latitude": latitude,
                    "longitude": longitude,
                    "source_type": "alert",
                    "headline": (
                        properties.get("headline")
                        or properties.get("event")
                        or "Weather Alert"
                    ),
                    "narrative_text": narrative_text,
                    "issued_at": properties.get("sent"),
                    "effective_at": properties.get("effective"),
                    "payload": alert,
                }
            )

        return documents
    

