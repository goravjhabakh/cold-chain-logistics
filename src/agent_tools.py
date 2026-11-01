import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from langchain_core.tools import tool
from openai import OpenAI
from sqlalchemy import create_engine, text

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

src_dir = Path(__file__).resolve().parent
project_root = src_dir.parent

load_dotenv(project_root / ".env")

agent_database_url = os.environ["AGENT_DATABASE_URL"]
openai_api_key = os.environ["OPENAI_API_KEY"]

embedding_model_name = os.getenv(
    "EMBEDDING_MODEL",
    "text-embedding-3-small",
)

embedding_dimensions = 1536

engine = create_engine(agent_database_url)
openai_client = OpenAI(api_key=openai_api_key)


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------


def format_rows(rows: list[dict]) -> str:
    if not rows:
        return "No matching shipments found."

    return "\n".join(str(row) for row in rows)


def generate_query_embedding(query: str) -> list[float]:
    response = openai_client.embeddings.create(
        model=embedding_model_name,
        input=query,
        dimensions=embedding_dimensions,
        encoding_format="float",
    )

    return response.data[0].embedding


# ---------------------------------------------------------
# Telemetry tools
# ---------------------------------------------------------


@tool
def find_shipments_near(
    latitude: float,
    longitude: float,
    radius_degrees: float = 1.0,
    limit: int = 10,
) -> str:
    """
    Find shipments near a geographic coordinate.

    Use this when the user asks about shipments near a city,
    location, latitude, or longitude.

    radius_degrees is an approximate latitude/longitude distance,
    not an exact physical distance.
    """

    query = text(
        """
        SELECT
            timestamp,
            latitude,
            longitude,
            current_temperature_c,
            cargo_condition,
            risk_classification,
            delay_probability,
            port_congestion_level,
            route_risk_index
        FROM agent_views.active_shipments
        WHERE latitude BETWEEN :min_latitude AND :max_latitude
          AND longitude BETWEEN :min_longitude AND :max_longitude
        ORDER BY timestamp DESC
        LIMIT :limit
        """
    )

    params = {
        "min_latitude": latitude - radius_degrees,
        "max_latitude": latitude + radius_degrees,
        "min_longitude": longitude - radius_degrees,
        "max_longitude": longitude + radius_degrees,
        "limit": limit,
    }

    try:
        with engine.connect() as connection:
            rows = connection.execute(query, params).mappings().all()

        return format_rows([dict(row) for row in rows])

    except Exception as exc:
        return f"Telemetry database error: {exc}"


@tool
def get_high_risk_shipments(limit: int = 10) -> str:
    """
    Find shipments classified as High Risk.

    Use this when the user asks about risky shipments,
    escalations, or shipments requiring attention.
    """

    query = text(
        """
        SELECT
            timestamp,
            latitude,
            longitude,
            current_temperature_c,
            cargo_condition,
            risk_classification,
            delay_probability,
            port_congestion_level,
            route_risk_index
        FROM agent_views.active_shipments
        WHERE risk_classification = 'High Risk'
        ORDER BY delay_probability DESC
        LIMIT :limit
        """
    )

    try:
        with engine.connect() as connection:
            rows = (
                connection.execute(
                    query,
                    {"limit": limit},
                )
                .mappings()
                .all()
            )

        return format_rows([dict(row) for row in rows])

    except Exception as exc:
        return f"Telemetry database error: {exc}"


@tool
def get_temperature_breaches(
    threshold_c: float = 4.0,
    limit: int = 10,
) -> str:
    """
    Find shipments whose current cargo temperature exceeds
    the supplied Celsius threshold.

    The default threshold is 4°C, but SOP retrieval should be
    used when the correct compliance threshold must be confirmed.
    """

    query = text(
        """
        SELECT
            timestamp,
            latitude,
            longitude,
            current_temperature_c,
            cargo_condition,
            risk_classification,
            delay_probability
        FROM agent_views.active_shipments
        WHERE current_temperature_c > :threshold
        ORDER BY current_temperature_c DESC
        LIMIT :limit
        """
    )

    try:
        with engine.connect() as connection:
            rows = (
                connection.execute(
                    query,
                    {
                        "threshold": threshold_c,
                        "limit": limit,
                    },
                )
                .mappings()
                .all()
            )

        return format_rows([dict(row) for row in rows])

    except Exception as exc:
        return f"Telemetry database error: {exc}"


# ---------------------------------------------------------
# SOP retrieval
# ---------------------------------------------------------


@tool
def search_compliance_sop(
    query: str,
    limit: int = 3,
) -> str:
    """
    Search cold-chain SOP and policy documents using semantic similarity.

    Use this for compliance thresholds, escalation rules,
    mitigation procedures, rerouting policies, and cargo handling guidance.
    """

    try:
        embedding = generate_query_embedding(query)

        vector = "[" + ",".join(map(str, embedding)) + "]"

        sql = text(
            """
            SELECT
                source_file,
                chunk_index,
                content,
                metadata,
                embedding <=> CAST(:embedding AS VECTOR) AS distance
            FROM sop_chunks
            ORDER BY embedding <=> CAST(:embedding AS VECTOR)
            LIMIT :limit
            """
        )

        with engine.connect() as connection:
            rows = (
                connection.execute(
                    sql,
                    {
                        "embedding": vector,
                        "limit": limit,
                    },
                )
                .mappings()
                .all()
            )

        if not rows:
            return "No matching compliance guidance found."

        results = []

        for row in rows:
            similarity = 1 - float(row["distance"])

            results.append(
                (
                    f"Source: {row['source_file']}\n"
                    f"Chunk: {row['chunk_index']}\n"
                    f"Similarity: {similarity:.4f}\n"
                    f"{row['content']}"
                )
            )

        return "\n\n---\n\n".join(results)

    except Exception as exc:
        return f"SOP retrieval error: {exc}"


# ---------------------------------------------------------
# External weather
# ---------------------------------------------------------


@tool
def fetch_corridor_conditions(
    latitude: float,
    longitude: float,
) -> str:
    """
    Fetch current external weather conditions for shipment coordinates.

    Use this when weather or environmental conditions may affect
    a shipment or transportation corridor.
    """

    try:
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": ("temperature_2m,wind_speed_10m,precipitation,weather_code"),
            },
            timeout=6,
        )

        response.raise_for_status()

        payload = response.json()
        current = payload.get("current", {})

        return (
            f"Location: {latitude}, {longitude}\n"
            f"Temperature: {current.get('temperature_2m', 'N/A')} °C\n"
            f"Wind speed: {current.get('wind_speed_10m', 'N/A')} km/h\n"
            f"Precipitation: {current.get('precipitation', 'N/A')} mm\n"
            f"Weather code: {current.get('weather_code', 'N/A')}"
        )

    except requests.RequestException as exc:
        return f"Weather API error: {exc}"


# ---------------------------------------------------------
# Local verification
# ---------------------------------------------------------


if __name__ == "__main__":
    print("\n--- Nearby shipments ---")
    print(
        find_shipments_near.invoke(
            {
                "latitude": 33.8,
                "longitude": -118.1,
                "radius_degrees": 1.0,
                "limit": 3,
            }
        )
    )

    print("\n--- High-risk shipments ---")
    print(get_high_risk_shipments.invoke({"limit": 3}))

    print("\n--- Temperature breaches ---")
    print(
        get_temperature_breaches.invoke(
            {
                "threshold_c": 4.0,
                "limit": 3,
            }
        )
    )

    print("\n--- SOP retrieval ---")
    print(
        search_compliance_sop.invoke(
            {
                "query": ("What should happen when fresh cargo exceeds 4 degrees Celsius?"),
                "limit": 3,
            }
        )
    )

    print("\n--- Weather ---")
    print(
        fetch_corridor_conditions.invoke(
            {
                "latitude": 33.8,
                "longitude": -118.1,
            }
        )
    )
