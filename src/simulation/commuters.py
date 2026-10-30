import numpy as np
import pandas as pd
import networkx as nx


# K.R. Market coordinates
MARKET_LAT = 12.9645
MARKET_LON = 77.5761889

# Commuter generation radius in metres
MAX_COMMUTER_RADIUS = 1200


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate geographic distance using the Haversine formula.
    Returns metres.
    """

    earth_radius = 6371000

    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)

    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1)
        * np.cos(lat2)
        * np.sin(dlon / 2) ** 2
    )

    return (
        2
        * earth_radius
        * np.arcsin(np.sqrt(a))
    )


def get_market_nodes(city):
    """
    Find actual road intersections around K.R. Market.

    Uses OSM node coordinates, not fictional districts.
    """

    market_nodes = []

    for node, data in city.nodes(data=True):

        lat = data.get("y", data.get("latitude"))
        lon = data.get("x", data.get("longitude"))

        if lat is None or lon is None:
            continue

        distance = calculate_distance(
            MARKET_LAT,
            MARKET_LON,
            lat,
            lon
        )

        if distance <= MAX_COMMUTER_RADIUS:

            market_nodes.append({
                "node": node,
                "distance": distance,
                "latitude": lat,
                "longitude": lon
            })

    if len(market_nodes) < 2:
        raise ValueError(
            "Not enough road intersections found around K.R. Market."
        )

    return market_nodes


def get_reachable_destination(
    city,
    origin,
    candidates,
    rng,
    max_attempts=30
):
    """
    Select a destination that can be reached from the origin.

    NetworkX checks the directed road network, so one-way
    roads are respected.
    """

    for _ in range(max_attempts):

        destination = rng.choice(candidates)

        if destination == origin:
            continue

        if nx.has_path(city, origin, destination):
            return destination

    return None


def generate_commuters(
    city,
    num_commuters=500,
    seed=42
):
    """
    Generate synthetic commuters using real Bengaluru
    road intersections around K.R. Market.

    Important:
    - Road geometry is real OSM data.
    - Commuter demand is synthetic.
    - Transport distribution is simulated.
    """

    if num_commuters <= 0:
        raise ValueError(
            "Number of commuters must be positive."
        )

    if city.number_of_nodes() == 0:
        raise ValueError(
            "City network cannot be empty."
        )

    rng = np.random.default_rng(seed)

    market_nodes = get_market_nodes(city)

    nodes = [
        item["node"]
        for item in market_nodes
    ]

    # Weight selection towards intersections closer to the market.
    distances = np.array([
        item["distance"]
        for item in market_nodes
    ])

    weights = 1 / (distances + 100)

    weights = weights / weights.sum()

    # More distant nodes are also useful for commuter origins.
    uniform_weights = np.ones(len(nodes)) / len(nodes)

    commuters = []

    transport_modes = [
        "car",
        "bus",
        "auto",
        "delivery"
    ]

    transport_probabilities = [
        0.45,
        0.25,
        0.20,
        0.10
    ]

    departure_periods = [
        ("morning", 420, 600),
        ("afternoon", 660, 840),
        ("evening", 960, 1140)
    ]

    attempts = 0
    max_total_attempts = num_commuters * 20

    while (
        len(commuters) < num_commuters
        and attempts < max_total_attempts
    ):

        attempts += 1

        # Origins are distributed around the wider area.
        origin = rng.choice(
            nodes,
            p=uniform_weights
        )

        # Destinations have higher probability near the market.
        destination = get_reachable_destination(
            city,
            origin,
            nodes,
            rng,
            max_attempts=20
        )

        if destination is None:
            continue

        # Departure time.
        period = rng.choice(
            len(departure_periods),
            p=[0.50, 0.20, 0.30]
        )

        period_name, start_minute, end_minute = (
            departure_periods[period]
        )

        departure_minute = int(
            rng.integers(
                start_minute,
                end_minute
            )
        )

        hours = departure_minute // 60
        minutes = departure_minute % 60

        departure_time = (
            f"{hours:02d}:{minutes:02d}"
        )

        transport_mode = rng.choice(
            transport_modes,
            p=transport_probabilities
        )

        origin_data = city.nodes[origin]
        destination_data = city.nodes[destination]

        origin_lat = origin_data.get(
            "y",
            origin_data.get("latitude")
        )

        origin_lon = origin_data.get(
            "x",
            origin_data.get("longitude")
        )

        destination_lat = destination_data.get(
            "y",
            destination_data.get("latitude")
        )

        destination_lon = destination_data.get(
            "x",
            destination_data.get("longitude")
        )

        commuters.append({

            "commuter_id": (
                f"C{len(commuters) + 1:04d}"
            ),

            "origin": origin,

            "destination": destination,

            "origin_lat": origin_lat,

            "origin_lon": origin_lon,

            "destination_lat": destination_lat,

            "destination_lon": destination_lon,

            "home_district": "K.R. Market Area",

            "work_district": "Bengaluru Urban Area",

            "departure_minute": departure_minute,

            "departure_time": departure_time,

            "departure_period": period_name,

            "transport_mode": transport_mode

        })

    if len(commuters) < num_commuters:

        raise RuntimeError(
            f"Generated only {len(commuters)} "
            f"of {num_commuters} commuters. "
            "Check network connectivity or increase "
            "the commuter generation radius."
        )

    return pd.DataFrame(commuters)


if __name__ == "__main__":

    from src.city.city import load_real_city

    city = load_real_city()

    commuters = generate_commuters(
        city,
        num_commuters=500
    )

    print("\nNOVACITY BENGALURU COMMUTER GENERATION")
    print("--------------------------------------")

    print("Total commuters:", len(commuters))

    print("\nTransport distribution:")

    print(
        commuters["transport_mode"]
        .value_counts()
        .to_string()
    )

    print("\nDeparture distribution:")

    print(
        commuters["departure_period"]
        .value_counts()
        .to_string()
    )

    print("\nSample commuters:")

    print(
        commuters[
            [
                "commuter_id",
                "origin",
                "destination",
                "transport_mode",
                "departure_time"
            ]
        ].head(10).to_string(index=False)
    )