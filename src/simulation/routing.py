
import networkx as nx
import math
import pandas as pd


def get_edge_weight(data):
    """Calculate realistic travel cost for one road segment."""

    if data.get("closed", False):
        return math.inf

    distance = float(data.get("distance", data.get("length", 1)))

    # Support both 'speed' and 'speed_limit' attributes.
    speed = max(
        float(data.get("speed_limit", data.get("speed", 25))),
        5
    )

    # Base travel time in minutes.
    base_time = float(
        data.get(
            "travel_time",
            (distance / 1000) / speed * 60
        )
    )

    if not math.isfinite(base_time) or base_time <= 0:
        base_time = max((distance / 1000) / speed * 60, 0.01)

    # Congestion penalty.
    utilisation = float(data.get("utilisation", 0))
    congestion_factor = 1 + 0.15 * max(utilisation, 0) ** 4

    # Accident penalty.
    accident_factor = 1.0

    if data.get("accident", False):
        severity = data.get("accident_severity", "moderate")

        accident_factor = {
            "low": 1.3,
            "moderate": 1.8,
            "high": 3.0,
            "critical": 6.0
        }.get(severity, 1.8)

    # Flood penalty.
    flood_factor = 1.0

    if data.get("flooded", False):
        depth = float(data.get("flood_depth", 0))

        if depth >= 0.50:
            return math.inf
        elif depth >= 0.30:
            flood_factor = 5.0
        elif depth >= 0.15:
            flood_factor = 2.5
        else:
            flood_factor = 1.5

    return base_time * congestion_factor * accident_factor * flood_factor


def edge_weight(u, v, data):
    """
    NetworkX-compatible weight callback.

    Supports:
    - Graph
    - DiGraph
    - MultiGraph
    - MultiDiGraph
    """

    # For MultiGraph, data contains:
    # {edge_key: {road attributes}}
    #
    # For Graph, data directly contains:
    # {road attribute: value}

    if data and all(isinstance(value, dict) for value in data.values()):
        weights = [
            get_edge_weight(edge_data)
            for edge_data in data.values()
        ]

        valid = [
            weight for weight in weights
            if math.isfinite(weight)
        ]

        return min(valid) if valid else math.inf

    # Normal Graph / DiGraph.
    return get_edge_weight(data)


def get_best_edge(graph, u, v):
    """Return the best usable physical road between two nodes."""

    candidates = []

    if graph.is_multigraph():

        for key, data in graph[u][v].items():
            weight = get_edge_weight(data)

            if math.isfinite(weight):
                candidates.append((weight, key, data))

    else:

        data = graph[u][v]
        weight = get_edge_weight(data)

        if math.isfinite(weight):
            candidates.append((weight, None, data))

    if not candidates:
        return None

    _, key, data = min(
        candidates,
        key=lambda item: item[0]
    )

    return {
        "u": u,
        "v": v,
        "key": key,
        "data": data
    }


def calculate_route(graph, origin, destination):
    """Calculate the fastest available route using Dijkstra."""

    if origin not in graph or destination not in graph:
        return None

    try:
        path = nx.shortest_path(
            graph,
            source=origin,
            target=destination,
            weight=edge_weight,
            method="dijkstra"
        )

    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None

    edges = []
    total_distance = 0.0
    total_time = 0.0

    for u, v in zip(path[:-1], path[1:]):

        edge = get_best_edge(graph, u, v)

        if edge is None:
            return None

        data = edge["data"]
        weight = get_edge_weight(data)

        if not math.isfinite(weight):
            return None

        distance = float(
            data.get("distance", data.get("length", 0))
        )

        edges.append({
            "u": u,
            "v": v,
            "key": edge["key"],
            "road_id": data.get("road_id"),
            "name": data.get("name", "Unnamed Road"),
            "distance": distance,
            "travel_time": weight
        })

        total_distance += distance
        total_time += weight

    return {
        "route": path,
        "edges": edges,
        "distance": total_distance,
        "travel_time": total_time
    }


def calculate_all_routes(graph, commuters):
    """Calculate routes for all commuters."""

    results = []

    for _, commuter in commuters.iterrows():

        result = calculate_route(
            graph,
            commuter["origin"],
            commuter["destination"]
        )

        if result is None:
            continue

        results.append({
            "commuter_id": commuter["commuter_id"],
            "origin": commuter["origin"],
            "destination": commuter["destination"],
            "route": result["route"],
            "edges": result["edges"],
            "distance": result["distance"],
            "travel_time": result["travel_time"],
            "transport_mode": commuter.get("transport_mode", "car")
        })

    return pd.DataFrame(results)

