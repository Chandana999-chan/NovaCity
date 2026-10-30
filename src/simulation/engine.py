import math
from copy import deepcopy

import pandas as pd

from src.events.events import apply_event
from src.simulation.traffic import (
    run_congestion_simulation,
    initialise_road_attributes
)
from src.simulation.signals import (
    initialise_signals,
    update_signals,
    get_signal_statistics
)
from src.simulation.vehicles import (
    initialise_vehicles,
    update_vehicles
)
from src.simulation.pedestrians import simulate_pedestrians


def safe_average(values):
    """Calculate average while ignoring invalid values."""

    valid = []

    for value in values:
        try:
            number = float(value)

            if math.isfinite(number):
                valid.append(number)

        except (TypeError, ValueError):
            continue

    return sum(valid) / len(valid) if valid else 0.0


def get_affected_roads(graph):
    """Collect roads affected by disruptions.

    Supports Graph, DiGraph, MultiGraph and MultiDiGraph.
    """

    affected = []

    if graph.is_multigraph():
        edges = graph.edges(keys=True, data=True)
    else:
        edges = (
            (u, v, None, data)
            for u, v, data in graph.edges(data=True)
        )

    for u, v, key, data in edges:

        if not any([
            data.get("accident", False),
            data.get("flooded", False),
            data.get("closed", False)
        ]):
            continue

        affected.append({
            "u": u,
            "v": v,
            "key": key,
            "road_id": data.get("road_id"),
            "road_name": data.get("name", "Unnamed Road"),
            "accident": data.get("accident", False),
            "flooded": data.get("flooded", False),
            "closed": data.get("closed", False),
            "flood_depth": data.get("flood_depth", 0),
            "accident_severity": data.get(
                "accident_severity", "none"
            ),
            "capacity": data.get("capacity", 0)
        })

    return affected

def compare_routes(baseline, disrupted):
    """Compare original and disrupted commuter journeys."""

    if baseline.empty or disrupted.empty:
        return pd.DataFrame()

    original = baseline.set_index("commuter_id")
    current = disrupted.set_index("commuter_id")

    common = original.index.intersection(current.index)

    records = []

    for commuter_id in common:

        old = original.loc[commuter_id]
        new = current.loc[commuter_id]

        old_route = list(old["route"])
        new_route = list(new["route"])

        old_time = float(old["travel_time"])
        new_time = float(new["travel_time"])

        records.append({
            "commuter_id": commuter_id,
            "original_route": old_route,
            "disrupted_route": new_route,
            "original_time": old_time,
            "disrupted_time": new_time,
            "extra_time": new_time - old_time,
            "route_changed": old_route != new_route,
            "delayed": new_time > old_time + 0.01
        })

    return pd.DataFrame(records)


def run_scenario(
    original_graph,
    commuters,
    events=None,
    simulation_hours=1,
    iterations=3,
    vehicle_limit=500,
    simulation_seconds=60,
    timestep=1
):
    """Run one independent city simulation scenario."""

    graph = deepcopy(original_graph)

    initialise_road_attributes(graph)

    initialise_signals(graph)

    # Apply scenario-specific events.
    applied_events = []

    for event in events or []:

        apply_event(graph, event)

        applied_events.append(event)

    # Calculate routes and congestion.
    traffic_result = run_congestion_simulation(
        graph,
        commuters,
        simulation_hours=simulation_hours,
        iterations=iterations
    )

    baseline_routes = traffic_result["baseline_routes"]
    final_routes = traffic_result["final_routes"]
    traffic = traffic_result["traffic"]
    changed_routes = traffic_result["changed_routes"]

    # Create vehicles from the final available routes.
    vehicles = initialise_vehicles(
        final_routes,
        max_vehicles=vehicle_limit
    )

    # Simulate vehicle movement and signal cycles.
    vehicle_history = []

    elapsed = 0

    while elapsed < simulation_seconds:

        update_signals(graph, elapsed_seconds=timestep)

        snapshot = update_vehicles(
            graph,
            vehicles,
            dt=timestep
        )

        vehicle_history.append({
            "elapsed_seconds": elapsed,
            "vehicles": snapshot
        })

        elapsed += timestep

    signal_statistics = get_signal_statistics(graph)

    # Pedestrian density simulation.
    pedestrians = simulate_pedestrians(graph)

    affected_roads = get_affected_roads(graph)

    return {
        "graph": graph,
        "baseline_routes": baseline_routes,
        "final_routes": final_routes,
        "traffic": traffic,
        "changed_routes": changed_routes,
        "vehicles": vehicles,
        "vehicle_history": vehicle_history,
        "events": applied_events,
        "affected_roads": affected_roads,
        "pedestrians": pedestrians,
        "signals": signal_statistics
    }


def run_simulation(
    graph,
    commuters,
    events=None,
    simulation_hours=1,
    iterations=3,
    vehicle_limit=500,
    simulation_seconds=60,
    timestep=1
):
    """Run baseline and disrupted simulations."""

    # Both scenarios start from the same original OSM graph.
    baseline = run_scenario(
        graph,
        commuters,
        events=[],
        simulation_hours=simulation_hours,
        iterations=iterations,
        vehicle_limit=vehicle_limit,
        simulation_seconds=simulation_seconds,
        timestep=timestep
    )

    disrupted = run_scenario(
        graph,
        commuters,
        events=events or [],
        simulation_hours=simulation_hours,
        iterations=iterations,
        vehicle_limit=vehicle_limit,
        simulation_seconds=simulation_seconds,
        timestep=timestep
    )

    baseline_routes = baseline["final_routes"]
    disrupted_routes = disrupted["final_routes"]

    comparison = compare_routes(
        baseline_routes,
        disrupted_routes
    )

    total_commuters = len(commuters)

    reachable = len(disrupted_routes)

    changed_count = (
        int(comparison["route_changed"].sum())
        if not comparison.empty else 0
    )

    delayed_count = (
        int(comparison["delayed"].sum())
        if not comparison.empty else 0
    )

    average_baseline_time = safe_average(
        baseline_routes["travel_time"]
        if not baseline_routes.empty else []
    )

    average_disrupted_time = safe_average(
        disrupted_routes["travel_time"]
        if not disrupted_routes.empty else []
    )

    traffic = disrupted["traffic"]

    congested_segments = (
        int((traffic["traffic_level"] == "High").sum())
        if not traffic.empty else 0
    )

    average_utilisation = safe_average(
        traffic["utilisation"]
        if not traffic.empty else []
    )

    summary = {
        "total_commuters": total_commuters,
        "reachable_commuters": reachable,
        "unreachable_commuters": total_commuters - reachable,
        "baseline_average_time": average_baseline_time,
        "disrupted_average_time": average_disrupted_time,
        "average_extra_time": (
            average_disrupted_time - average_baseline_time
        ),
        "changed_routes": changed_count,
        "delayed_commuters": delayed_count,
        "average_road_utilisation": average_utilisation,
        "congested_road_segments": congested_segments,
        "events_applied": len(disrupted["events"]),
        "affected_road_segments": len(disrupted["affected_roads"]),
        "active_vehicles": len(disrupted["vehicles"]),
        "completed_vehicles": sum(
            vehicle["completed"]
            for vehicle in disrupted["vehicles"]
        ),
        "pedestrian_count": len(disrupted["pedestrians"]),
        "signal_count": disrupted["signals"]["total_signals"]
    }

    return {
        "summary": summary,
        "baseline": baseline,
        "disrupted": disrupted,
        "comparison": comparison
    }