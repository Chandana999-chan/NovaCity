import math
import random


MARKET_LAT = 12.9645
MARKET_LON = 77.5761889


def haversine(lat1, lon1, lat2, lon2):

    radius = 6371000

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)

    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    return radius * 2 * math.asin(math.sqrt(a))


def simulate_pedestrians(
    graph,
    time_period="Morning",
    seed=42
):

    random.seed(seed)

    period_multiplier = {
        "Morning": 1.5,
        "Afternoon": 1.2,
        "Evening": 1.8
    }.get(time_period, 1.0)

    records = []

    for node, data in graph.nodes(data=True):

        lat = data.get("y")
        lon = data.get("x")

        if lat is None or lon is None:
            continue

        distance = haversine(
            MARKET_LAT,
            MARKET_LON,
            lat,
            lon
        )

        # Higher crowd density closer to the market.
        density = max(
            0,
            1 - distance / 1500
        )

        count = int(
            random.randint(0, 15)
            + density * 120 * period_multiplier
        )

        data["pedestrian_count"] = count

        if count >= 100:
            level = "Very High"
        elif count >= 60:
            level = "High"
        elif count >= 25:
            level = "Medium"
        else:
            level = "Low"

        records.append({
            "node": node,
            "latitude": lat,
            "longitude": lon,
            "distance_from_market": distance,
            "pedestrian_count": count,
            "crowd_level": level
        })

    return records