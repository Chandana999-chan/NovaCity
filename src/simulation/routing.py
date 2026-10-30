import networkx as nx
import pandas as pd


def get_best_edge(city, u, v, weight="travel_time"):
    """
    Return the best available edge between two nodes.

    A MultiDiGraph may have multiple parallel road segments
    between the same pair of nodes.

    The edge with the lowest travel time is selected.
    Closed roads are excluded.
    """

    if not city.has_edge(u, v):
        return None, None

    if city.is_multigraph():

        candidates = city[u][v]

        available = []

        for key, data in candidates.items():

            if data.get("closed", False):
                continue

            edge_weight = data.get(weight, float("inf"))

            if edge_weight is None:
                continue

            try:
                edge_weight = float(edge_weight)
            except (TypeError, ValueError):
                continue

            if edge_weight < 0 or edge_weight == float("inf"):
                continue

            available.append((key, data))

        if not available:
            return None, None

        return min(
            available,
            key=lambda item: float(
                item[1].get(weight, float("inf"))
            )
        )

    data = city[u][v]

    if data.get("closed", False):
        return None, None

    return 0, data


def get_edge_weight(city, u, v, weight="travel_time"):
    """
    NetworkX weight callback.

    Returns None for unavailable roads.
    """

    key, data = get_best_edge(
        city,
        u,
        v,
        weight
    )

    if data is None:
        return None

    value = data.get(weight, float("inf"))

    try:
        value = float(value)
    except (TypeError, ValueError):
        return None

    if value < 0 or value == float("inf"):
        return None

    return value


def calculate_route(
    city,
    origin,
    destination,
    weight="travel_time"
):
    """
    Find the shortest available route.

    Supports:
    - Directed roads
    - One-way roads
    - Parallel road segments
    - Closed roads
    - Congestion-adjusted travel times

    Returns node route and the selected edge details.
    """

    if origin not in city or destination not in city:

        return {
            "route": [],
            "distance": None,
            "travel_time": None,
            "edges": []
        }

    if origin == destination:

        return {
            "route": [origin],
            "distance": 0,
            "travel_time": 0,
            "edges": []
        }

    # Create a view that excludes closed roads.
    if city.is_multigraph():

        available_city = nx.subgraph_view(
            city,
            filter_edge=lambda u, v, key: (
                not city.edges[u, v, key].get(
                    "closed", False
                )
            )
        )

    else:

        available_city = nx.subgraph_view(
            city,
            filter_edge=lambda u, v: (
                not city.edges[u, v].get(
                    "closed", False
                )
            )
        )

    try:

        route = nx.shortest_path(
            available_city,
            source=origin,
            target=destination,
            weight=lambda u, v, data: get_edge_weight(
                city,
                u,
                v,
                weight
            )
        )

        total_distance = 0.0
        total_travel_time = 0.0
        selected_edges = []

        # Resolve the actual road segment used between
        # each pair of consecutive intersections.
        for u, v in zip(route[:-1], route[1:]):

            key, data = get_best_edge(
                city,
                u,
                v,
                weight
            )

            if data is None:
                raise nx.NetworkXNoPath(
                    f"No usable road between {u} and {v}"
                )

            distance = float(
                data.get("distance", 0)
            )

            travel_time = float(
                data.get("travel_time", 0)
            )

            total_distance += distance
            total_travel_time += travel_time

            selected_edges.append({
                "start": u,
                "end": v,
                "key": key,
                "road_id": data.get(
                    "road_id",
                    f"{u}_{v}_{key}"
                ),
                "name": data.get("name", "Unnamed road"),
                "distance": distance,
                "travel_time": travel_time
            })

        return {
            "route": route,
            "distance": total_distance,
            "travel_time": total_travel_time,
            "edges": selected_edges
        }

    except (
        nx.NetworkXNoPath,
        nx.NodeNotFound
    ):

        return {
            "route": [],
            "distance": None,
            "travel_time": None,
            "edges": []
        }


def calculate_all_routes(city, commuters):
    """
    Calculate routes for all commuters.
    """

    results = []

    for _, commuter in commuters.iterrows():

        result = calculate_route(
            city=city,
            origin=commuter["origin"],
            destination=commuter["destination"],
            weight="travel_time"
        )

        results.append({

            "commuter_id": commuter["commuter_id"],

            "origin": commuter["origin"],

            "destination": commuter["destination"],

            "route": result["route"],

            "distance": result["distance"],

            "travel_time": result["travel_time"],

            "edges": result["edges"],

            "transport_mode": commuter["transport_mode"]

        })

    return pd.DataFrame(results)