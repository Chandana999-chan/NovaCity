import math
import random

from shapely.geometry import LineString, Point


VEHICLE_CONFIG = {
    "car": {
        "max_speed": 11.0,
        "acceleration": 2.0,
        "braking": 4.0,
        "length": 4.5
    },
    "bus": {
        "max_speed": 7.0,
        "acceleration": 1.0,
        "braking": 3.0,
        "length": 11.0
    },
    "auto": {
        "max_speed": 8.0,
        "acceleration": 1.5,
        "braking": 3.5,
        "length": 3.0
    },
    "delivery": {
        "max_speed": 8.0,
        "acceleration": 1.2,
        "braking": 3.0,
        "length": 6.0
    }
}


def get_edge(graph, u, v, key=None):
    """Retrieve road attributes from Graph or MultiGraph."""

    if not graph.has_edge(u, v):
        return None

    # MultiGraph / MultiDiGraph
    if graph.is_multigraph():

        edge_data = graph[u][v]

        if key is not None and key in edge_data:
            return edge_data[key]

        if not edge_data:
            return None

        # Fall back to the first available parallel road.
        return next(iter(edge_data.values()))

    # Graph / DiGraph
    return graph[u][v]


def get_edge_geometry(graph, u, v, key):
    """Return road geometry, falling back to node coordinates."""

    data = get_edge(graph, u, v, key)

    if data is None:
        return None

    geometry = data.get("geometry")

    if geometry is not None:
        return geometry

    start = graph.nodes[u]
    end = graph.nodes[v]

    return LineString([
        (start["x"], start["y"]),
        (end["x"], end["y"])
    ])


def get_vehicle_position(graph, vehicle):
    """Calculate geographic position along the current road."""

    u = vehicle["current_node"]
    v = vehicle["next_node"]
    key = vehicle["edge_key"]

    geometry = get_edge_geometry(graph, u, v, key)

    if geometry is None:
        return None

    length = max(geometry.length, 0.000001)

    fraction = min(
        max(vehicle["edge_progress"] / max(
            vehicle["edge_distance"], 0.001
        ), 0),
        1
    )

    point = geometry.interpolate(fraction * length)

    return {
        "lat": point.y,
        "lon": point.x
    }


def create_vehicle(vehicle_id, commuter):
    """Create an individual vehicle from a commuter route."""

    mode = commuter.get("transport_mode", "car")

    if mode not in VEHICLE_CONFIG:
        mode = "car"

    route = commuter["route"]
    edges = commuter["edges"]

    if not route or not edges:
        return None

    config = VEHICLE_CONFIG[mode]

    return {
        "vehicle_id": vehicle_id,
        "commuter_id": commuter["commuter_id"],
        "vehicle_type": mode,

        "route": list(route),
        "edges": list(edges),

        "edge_index": 0,
        "current_node": edges[0]["u"],
        "next_node": edges[0]["v"],
        "edge_key": edges[0]["key"],

        "edge_progress": 0.0,
        "edge_distance": max(
            float(edges[0].get("distance", 1)), 0.1
        ),

        "speed": 0.0,
        "max_speed": config["max_speed"],
        "acceleration": config["acceleration"],
        "braking": config["braking"],
        "length": config["length"],

        "status": "MOVING",
        "completed": False
    }


def initialise_vehicles(routes, max_vehicles=500, seed=42):
    """Create a vehicle fleet from calculated commuter routes."""

    random.seed(seed)

    vehicles = []

    if routes is None or routes.empty:
        return vehicles

    selected = routes.head(max_vehicles)

    for index, (_, commuter) in enumerate(selected.iterrows()):

        vehicle = create_vehicle(index + 1, commuter)

        if vehicle is not None:
            vehicles.append(vehicle)

    return vehicles


def get_vehicle_speed_limit(graph, vehicle):
    """Get speed limit from the current road."""

    data = get_edge(
        graph,
        vehicle["current_node"],
        vehicle["next_node"],
        vehicle["edge_key"]
    )

    if data is None:
        return 0

    road_limit = float(data.get("speed_limit", 30))

    # Convert km/h to m/s.
    return min(
        vehicle["max_speed"],
        road_limit / 3.6
    )


def is_signal_blocking(graph, vehicle):
    """Check whether the next intersection blocks the vehicle."""

    node = vehicle["next_node"]
    attributes = graph.nodes[node]

    if not attributes.get("signalized", False):
        return False

    state = str(attributes.get("state", "GREEN")).upper()

    return state not in ("GREEN", "NONE")


def get_vehicle_ahead(vehicle, vehicles):
    """Find the nearest vehicle ahead on the same directed segment."""

    nearest_gap = float("inf")

    for other in vehicles:

        if other is vehicle or other["completed"]:
            continue

        same_edge = (
            other["current_node"] == vehicle["current_node"]
            and other["next_node"] == vehicle["next_node"]
            and other["edge_key"] == vehicle["edge_key"]
        )

        if not same_edge:
            continue

        if other["edge_progress"] <= vehicle["edge_progress"]:
            continue

        gap = (
            other["edge_progress"]
            - vehicle["edge_progress"]
            - other["length"]
        )

        nearest_gap = min(nearest_gap, gap)

    return nearest_gap


def advance_vehicle(graph, vehicle, vehicles, dt=1.0):
    """Advance one vehicle by one simulation timestep."""

    if vehicle["completed"]:
        return

    u = vehicle["current_node"]
    v = vehicle["next_node"]
    key = vehicle["edge_key"]

    data = get_edge(graph, u, v, key)

    if data is None or data.get("closed", False):
        vehicle["speed"] = 0
        vehicle["status"] = "ROAD_BLOCKED"
        return

    if data.get("flooded", False) and float(
        data.get("flood_depth", 0)
    ) >= 0.50:
        vehicle["speed"] = 0
        vehicle["status"] = "FLOODED"
        return

    speed_limit = get_vehicle_speed_limit(graph, vehicle)

    # Reduce speed on accident-affected roads.
    if data.get("accident", False):
        speed_limit *= 0.5

    # Reduce speed in flooded areas.
    if data.get("flooded", False):
        speed_limit *= 0.4

    distance_remaining = (
        vehicle["edge_distance"] - vehicle["edge_progress"]
    )

    gap = get_vehicle_ahead(vehicle, vehicles)

    # Maintain minimum following distance.
    safe_gap = max(5.0, vehicle["speed"] * 1.5)

    signal_blocked = (
        is_signal_blocking(graph, vehicle)
        and distance_remaining < 30
    )

    blocked = signal_blocked or gap < safe_gap

    if blocked:
        target_speed = 0.0
        vehicle["status"] = (
            "WAITING_SIGNAL" if signal_blocked else "QUEUED"
        )
    else:
        target_speed = speed_limit
        vehicle["status"] = "MOVING"

    # Accelerate or brake.
    if target_speed > vehicle["speed"]:
        vehicle["speed"] = min(
            target_speed,
            vehicle["speed"] + vehicle["acceleration"] * dt
        )
    else:
        vehicle["speed"] = max(
            target_speed,
            vehicle["speed"] - vehicle["braking"] * dt
        )

    movement = vehicle["speed"] * dt

    # Prevent passing the next intersection while its signal is red.
    if signal_blocked:
        movement = min(movement, max(distance_remaining - 2, 0))

    if gap < safe_gap:
        movement = min(movement, max(gap - 2, 0))

    vehicle["edge_progress"] += movement

    # Move to the next road segment.
    if vehicle["edge_progress"] >= vehicle["edge_distance"]:

        vehicle["edge_index"] += 1

        if vehicle["edge_index"] >= len(vehicle["edges"]):
            vehicle["completed"] = True
            vehicle["status"] = "COMPLETED"
            vehicle["speed"] = 0
            return

        next_edge = vehicle["edges"][vehicle["edge_index"]]

        vehicle["current_node"] = next_edge["u"]
        vehicle["next_node"] = next_edge["v"]
        vehicle["edge_key"] = next_edge["key"]

        vehicle["edge_distance"] = max(
            float(next_edge.get("distance", 1)), 0.1
        )

        vehicle["edge_progress"] = 0.0


def update_vehicles(graph, vehicles, dt=1.0):
    """Update the entire vehicle fleet."""

    # Process vehicles nearest to the end of each edge first.
    ordered = sorted(
        vehicles,
        key=lambda vehicle: (
            vehicle["current_node"],
            vehicle["next_node"],
            vehicle["edge_key"],
            -vehicle["edge_progress"]
        )
    )

    for vehicle in ordered:
        advance_vehicle(graph, vehicle, vehicles, dt)

    return get_vehicle_snapshot(graph, vehicles)


def get_vehicle_snapshot(graph, vehicles):
    """Return current vehicle positions for the dashboard."""

    records = []

    for vehicle in vehicles:

        if vehicle["completed"]:
            continue

        position = get_vehicle_position(graph, vehicle)

        if position is None:
            continue

        records.append({
            "vehicle_id": vehicle["vehicle_id"],
            "commuter_id": vehicle["commuter_id"],
            "vehicle_type": vehicle["vehicle_type"],
            "lat": position["lat"],
            "lon": position["lon"],
            "speed": round(vehicle["speed"] * 3.6, 2),
            "status": vehicle["status"],
            "current_node": vehicle["current_node"],
            "next_node": vehicle["next_node"]
        })

    return records