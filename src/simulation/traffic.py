import networkx as nx
import pandas as pd

from src.simulation.routing import calculate_all_routes


def get_road_edges(city):
    """
    Return every road segment.

    Supports:
    - OSMnx MultiDiGraph / MultiGraph
    - NetworkX DiGraph / Graph
    """

    if city.is_multigraph():
        return list(city.edges(keys=True, data=True))

    return [
        (u, v, 0, data)
        for u, v, data in city.edges(data=True)
    ]


def get_edge_data(city, u, v):
    """
    Find the best usable parallel edge between two nodes.

    For a MultiDiGraph, multiple road segments may connect
    the same pair of nodes. Select the one with the lowest
    current travel time.
    """

    if not city.has_edge(u, v):
        return None, None

    if city.is_multigraph():
        candidates = city[u][v]

        usable = [
            (key, data)
            for key, data in candidates.items()
            if not data.get("closed", False)
        ]

        if not usable:
            return None, None

        return min(
            usable,
            key=lambda item: item[1].get(
                "travel_time", float("inf")
            )
        )

    data = city[u][v]

    if data.get("closed", False):
        return None, None

    return 0, data


def calculate_free_flow_time(distance, speed):
    """
    Calculate free-flow travel time in minutes.

    OSMnx:
    - distance is in metres
    - speed is in kilometres per hour

    Formula:
    minutes = distance(m) * 0.06 / speed(km/h)
    """

    speed = max(float(speed), 1.0)
    distance = max(float(distance), 0.0)

    return (distance * 0.06) / speed


def initialise_road_attributes(city):
    """
    Initialise simulation attributes on every road segment.
    """

    for u, v, key, data in get_road_edges(city):

        distance = float(data.get("distance", 100))

        speed = float(
            data.get(
                "speed",
                data.get("speed_kph", 30)
            )
        )

        lanes = max(int(data.get("lanes", 1)), 1)

        capacity = float(
            data.get("capacity", lanes * 600)
        )

        free_flow_time = calculate_free_flow_time(
            distance,
            speed
        )

        data.setdefault("road_id", f"{u}_{v}_{key}")
        data["distance"] = distance
        data["speed"] = speed
        data["lanes"] = lanes
        data["capacity"] = max(capacity, 1)

        data.setdefault("traffic", 0.0)
        data.setdefault("utilisation", 0.0)
        data.setdefault("vehicle_count", 0)
        data.setdefault("queue_length", 0)
        data.setdefault("event_factor", 1.0)

        data["free_flow_time"] = free_flow_time

        if data.get("closed", False):
            data["travel_time"] = float("inf")
        else:
            data["travel_time"] = (
                free_flow_time * data["event_factor"]
            )


def calculate_traffic(city, routes, simulation_hours=3):
    """
    Calculate traffic volume, utilisation and congestion-adjusted
    travel time for every road segment.

    Each car commuter represents one vehicle.
    Bus commuters are counted as passengers, not physical buses.

    This is an aggregate traffic assignment model, not yet
    a vehicle-by-vehicle movement simulation.
    """

    if simulation_hours <= 0:
        raise ValueError("Simulation hours must be positive.")

    if routes is None or routes.empty:
        raise ValueError("Route data is empty.")

    road_counts = {}

    # Initialise a separate counter for every directed road segment.
    for u, v, key, data in get_road_edges(city):

        road_id = data.get(
            "road_id",
            f"{u}_{v}_{key}"
        )

        road_counts[(u, v, key)] = {
            "road_id": road_id,
            "car_traversals": 0,
            "bus_passengers": 0
        }

    # Count commuter movements.
    for _, commuter in routes.iterrows():

        route = commuter.get("route", None)
        transport_mode = commuter.get(
            "transport_mode", "car"
        )

        if not isinstance(route, (list, tuple)):
            continue

        for u, v in zip(route[:-1], route[1:]):

            key, edge_data = get_edge_data(city, u, v)

            # Skip missing or closed road segments.
            if edge_data is None:
                continue

            edge_key = (u, v, key)

            if edge_key not in road_counts:
                continue

            if transport_mode == "car":
                road_counts[edge_key]["car_traversals"] += 1

            elif transport_mode == "bus":
                road_counts[edge_key]["bus_passengers"] += 1

    road_results = []

    # Calculate congestion for every road segment.
    for u, v, key, data in get_road_edges(city):

        counts = road_counts[(u, v, key)]

        car_traversals = counts["car_traversals"]
        bus_passengers = counts["bus_passengers"]

        capacity = max(float(data["capacity"]), 1)

        vehicles_per_hour = (
            car_traversals / simulation_hours
        )

        utilisation_ratio = vehicles_per_hour / capacity
        utilisation_percent = utilisation_ratio * 100

        free_flow_time = data["free_flow_time"]

        event_factor = max(
            float(data.get("event_factor", 1.0)),
            1.0
        )

        closed = data.get("closed", False)

        # BPR-style congestion calculation.
        congestion_factor = (
            1 + 0.15 * (utilisation_ratio ** 4)
        )

        if closed:
            travel_time = float("inf")
        else:
            travel_time = (
                free_flow_time
                * congestion_factor
                * event_factor
            )

        # Update actual graph edge attributes.
        data["traffic"] = vehicles_per_hour
        data["utilisation"] = utilisation_ratio
        data["vehicle_count"] = car_traversals
        data["travel_time"] = travel_time

        road_results.append({
            "road_id": counts["road_id"],
            "road": data.get("name", f"{u}-{v}"),
            "start": u,
            "end": v,
            "key": key,
            "car_traversals": car_traversals,
            "bus_passengers": bus_passengers,
            "vehicles_per_hour": round(
                vehicles_per_hour, 2
            ),
            "capacity": capacity,
            "utilisation": round(
                utilisation_percent, 2
            ),
            "free_flow_time": round(
                free_flow_time, 4
            ),
            "travel_time": (
                round(travel_time, 4)
                if travel_time != float("inf")
                else None
            ),
            "closed": closed,
            "flooded": data.get("flooded", False),
            "accident": data.get("accident", False)
        })

    return pd.DataFrame(road_results)


def run_congestion_simulation(
    city,
    commuters,
    simulation_hours=3,
    iterations=3
):
    """
    Run iterative congestion-aware traffic assignment.

    The routing module recalculates commuter routes using
    updated congestion-adjusted travel times.
    """

    if iterations < 1:
        raise ValueError("Iterations must be at least 1.")

    if commuters is None or commuters.empty:
        raise ValueError("Commuter data is empty.")

    initialise_road_attributes(city)

    # Baseline route assignment.
    baseline_routes = calculate_all_routes(
        city,
        commuters
    )

    baseline_traffic = calculate_traffic(
        city,
        baseline_routes,
        simulation_hours
    )

    current_routes = baseline_routes
    current_traffic = baseline_traffic

    # Congestion-aware iterations.
    for iteration in range(iterations):

        print(
            f"\nTraffic iteration: "
            f"{iteration + 1}/{iterations}"
        )

        current_routes = calculate_all_routes(
            city,
            commuters
        )

        current_traffic = calculate_traffic(
            city,
            current_routes,
            simulation_hours
        )

    # Count changed commuter routes.
    changed_routes = 0

    if (
        "route" in baseline_routes.columns
        and "route" in current_routes.columns
    ):

        for old_route, new_route in zip(
            baseline_routes["route"],
            current_routes["route"]
        ):

            if old_route != new_route:
                changed_routes += 1

    return {
        "baseline_routes": baseline_routes,
        "final_routes": current_routes,
        "baseline_traffic": baseline_traffic,
        "final_traffic": current_traffic,
        "changed_routes": changed_routes
    }