
import math
import pandas as pd

from src.simulation.routing import calculate_all_routes


MODE_FACTORS = {
    "car": 1.0,
    "auto": 0.7,
    "bus": 2.5,
    "delivery": 1.2
}


def get_edge_id(graph, u, v, key=None):
    """
    Generate a consistent road identifier.

    Handles normal Graph and MultiGraph structures.
    Undirected roads use the same ID in either direction.
    """

    if not graph.is_directed():
        if str(u) > str(v):
            u, v = v, u

    return u, v, key if graph.is_multigraph() else None


def iter_roads(graph):
    """Yield every road in a consistent format."""

    if graph.is_multigraph():
        for u, v, key, data in graph.edges(keys=True, data=True):
            yield u, v, key, data
    else:
        for u, v, data in graph.edges(data=True):
            yield u, v, None, data


def initialise_road_attributes(graph):
    """Initialise road attributes for all supported NetworkX graph types."""

    for u, v, key, data in iter_roads(graph):

        distance = float(
            data.get("distance", data.get("length", 1))
        )

        # NovaCity's current city network uses distance in kilometres
        # and speed in kilometres per hour.
        speed = max(
            float(data.get("speed", data.get("speed_limit", 25))),
            5.0
        )

        free_flow_time = distance / speed * 60

        data.setdefault("traffic", 0)
        data.setdefault("vehicle_count", 0)
        data.setdefault("weighted_load", 0)
        data.setdefault("utilisation", 0.0)
        data.setdefault("queue_length", 0)
        data.setdefault("event_factor", 1.0)
        data.setdefault("closed", False)

        data["free_flow_time"] = free_flow_time

        if not data.get("travel_time") or data["travel_time"] <= 0:
            data["travel_time"] = free_flow_time

    return graph


def calculate_traffic(graph, routes, simulation_hours=1):
    """Calculate road usage, capacity utilisation and congestion."""

    simulation_hours = max(float(simulation_hours), 0.01)

    usage = {}

    # Initialise usage for every road.
    for u, v, key, data in iter_roads(graph):

        edge_id = get_edge_id(graph, u, v, key)

        usage[edge_id] = {
            "vehicles": 0,
            "weighted_load": 0.0
        }

    # Count commuter usage.
    for _, commuter in routes.iterrows():

        mode = commuter.get("transport_mode", "car")
        factor = MODE_FACTORS.get(mode, 1.0)

        for edge in commuter.get("edges", []):

            edge_id = get_edge_id(
                graph,
                edge["u"],
                edge["v"],
                edge.get("key")
            )

            if edge_id not in usage:
                continue

            usage[edge_id]["vehicles"] += 1
            usage[edge_id]["weighted_load"] += factor

    records = []

    # Calculate traffic for every road.
    for u, v, key, data in iter_roads(graph):

        edge_id = get_edge_id(graph, u, v, key)
        road_usage = usage[edge_id]

        vehicles = road_usage["vehicles"]
        load = road_usage["weighted_load"]

        capacity = max(float(data.get("capacity", 1)), 1)
        hourly_capacity = capacity * simulation_hours

        utilisation = load / hourly_capacity

        # Bureau of Public Roads-style congestion model.
        congestion_factor = 1 + 0.15 * (utilisation ** 4)

        base_time = float(data["free_flow_time"])

        if data.get("closed", False):
            travel_time = math.inf
        else:
            travel_time = (
                base_time
                * congestion_factor
                * float(data.get("event_factor", 1.0))
            )

        if utilisation < 0.50:
            level = "Low"
        elif utilisation < 0.85:
            level = "Medium"
        else:
            level = "High"

        queue = max(0, load - hourly_capacity)

        # Update the actual graph edge.
        data["vehicle_count"] = vehicles
        data["traffic"] = vehicles
        data["weighted_load"] = load
        data["vehicles_per_hour"] = vehicles / simulation_hours
        data["utilisation"] = utilisation
        data["congestion_factor"] = congestion_factor
        data["travel_time"] = travel_time
        data["queue_length"] = queue
        data["traffic_level"] = level

        records.append({
            "u": u,
            "v": v,
            "start": u,
            "end": v,
            "key": key,
            "road_id": data.get("road_id"),
            "road_name": data.get("name", "Unnamed Road"),
            "vehicles": vehicles,
            "vehicles_per_hour": vehicles / simulation_hours,
            "capacity": capacity,
            "utilisation": utilisation,
            "queue_length": queue,
            "free_flow_time": base_time,
            "travel_time": travel_time,
            "traffic_level": level,
            "closed": data.get("closed", False),
            "accident": data.get("accident", False),
            "flooded": data.get("flooded", False)
        })

    return pd.DataFrame(records)


def find_changed_routes(baseline, updated):
    """Identify commuters whose routes changed."""

    if baseline is None or updated is None:
        return pd.DataFrame()

    if baseline.empty or updated.empty:
        return pd.DataFrame()

    original = baseline.set_index("commuter_id")
    current = updated.set_index("commuter_id")

    common = original.index.intersection(current.index)

    changed = []

    for commuter_id in common:

        old_route = original.loc[commuter_id, "route"]
        new_route = current.loc[commuter_id, "route"]

        if list(old_route) != list(new_route):

            changed.append({
                "commuter_id": commuter_id,
                "old_route": old_route,
                "new_route": new_route,
                "old_time": original.loc[
                    commuter_id, "travel_time"
                ],
                "new_time": current.loc[
                    commuter_id, "travel_time"
                ]
            })

    return pd.DataFrame(changed)


def run_congestion_simulation(
    graph,
    commuters,
    simulation_hours=1,
    iterations=3
):
    """
    Run iterative congestion simulation.

    Returns the four keys required by engine.py:
    baseline_routes, final_routes, traffic, changed_routes.
    """

    initialise_road_attributes(graph)

    # Step 1: Calculate original routes before congestion updates.
    baseline_routes = calculate_all_routes(
        graph,
        commuters
    )

    if baseline_routes is None:
        baseline_routes = pd.DataFrame()

    # Keep a separate copy for route comparison.
    baseline_routes = baseline_routes.copy(deep=True)

    current_routes = baseline_routes.copy(deep=True)

    # Step 2: Iteratively calculate congestion and update routes.
    for _ in range(max(1, int(iterations))):

        if current_routes.empty:
            break

        traffic_df = calculate_traffic(
            graph,
            current_routes,
            simulation_hours
        )

        # Update road travel times.
        for _, row in traffic_df.iterrows():

            u = row["u"]
            v = row["v"]

            if not graph.has_edge(u, v):
                continue

            if graph.is_multigraph():

                key = row["key"]

                if graph.has_edge(u, v, key):
                    graph[u][v][key]["travel_time"] = row[
                        "travel_time"
                    ]

            else:
                graph[u][v]["travel_time"] = row[
                    "travel_time"
                ]

        # Recalculate commuter routes.
        updated_routes = calculate_all_routes(
            graph,
            commuters
        )

        if updated_routes is None or updated_routes.empty:
            break

        if (
            "route" in current_routes.columns
            and "route" in updated_routes.columns
        ):

            old = current_routes.set_index(
                "commuter_id"
            )["route"]

            new = updated_routes.set_index(
                "commuter_id"
            )["route"]

            common = old.index.intersection(new.index)

            unchanged = all(
                list(old.loc[cid]) == list(new.loc[cid])
                for cid in common
            )

            current_routes = updated_routes

            if unchanged:
                break

        else:
            current_routes = updated_routes

    # Step 3: Calculate final traffic metrics.
    final_traffic = calculate_traffic(
        graph,
        current_routes,
        simulation_hours
    )

    # Step 4: Identify changed commuter routes.
    changed_routes = find_changed_routes(
        baseline_routes,
        current_routes
    )

    # Return exactly what engine.py expects.
    return {
        "baseline_routes": baseline_routes,
        "final_routes": current_routes,
        "traffic": final_traffic,
        "changed_routes": changed_routes
    }

