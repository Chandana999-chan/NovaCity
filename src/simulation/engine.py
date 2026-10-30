from copy import deepcopy
import math

from src.simulation.traffic import (
    run_congestion_simulation,
    initialise_road_attributes
)


def get_target_edges(graph, road):
    """
    Resolve an event target to actual road segments.

    Supported formats:

    1. (u, v)
       Applies to all parallel edges in that direction.

    2. (u, v, key)
       Applies to one exact road segment.

    3. road_id string
       Applies to the segment with that road_id.
    """

    targets = []

    if isinstance(road, str):

        for u, v, key, data in graph.edges(
            keys=True,
            data=True
        ):

            if data.get("road_id") == road:
                targets.append((u, v, key))

    elif isinstance(road, (tuple, list)):

        if len(road) == 2:

            u, v = road

            if graph.has_edge(u, v):

                for key in graph[u][v]:
                    targets.append((u, v, key))

        elif len(road) == 3:

            u, v, key = road

            if graph.has_edge(u, v, key):
                targets.append((u, v, key))

    if not targets:
        raise ValueError(
            f"No matching road segment found for event: {road}"
        )

    return targets


def apply_event(graph, event):
    """
    Apply an event to a specific scenario graph.

    Event examples:

    {
        "type": "road_closure",
        "road": (123, 456)
    }

    {
        "type": "accident",
        "road": (123, 456, 0)
    }

    {
        "type": "flood",
        "road": "123_456_0"
    }
    """

    event_type = event.get("type")
    road = event.get("road")

    supported_events = {
        "road_closure",
        "accident",
        "flood"
    }

    if event_type not in supported_events:
        raise ValueError(
            f"Unsupported event type: {event_type}"
        )

    targets = get_target_edges(graph, road)

    for u, v, key in targets:

        data = graph.edges[u, v, key]

        if event_type == "road_closure":

            data["closed"] = True
            data["closure"] = True

        elif event_type == "accident":

            data["accident"] = True

            # Represent an accident as reduced road capacity.
            data["capacity"] = max(
                float(data.get("capacity", 600)) * 0.5,
                1
            )

            data["event_factor"] = (
                float(data.get("event_factor", 1.0)) * 1.5
            )

        elif event_type == "flood":

            data["flooded"] = True

            # Flooding reduces usable road capacity.
            data["capacity"] = max(
                float(data.get("capacity", 600)) * 0.3,
                1
            )

            data["event_factor"] = (
                float(data.get("event_factor", 1.0)) * 2.0
            )

    return len(targets)


def get_commuter_times(routes):
    """
    Get actual route travel times.

    Uses the selected road segments returned by routing.py.
    This avoids ambiguity when multiple roads connect
    the same intersections.
    """

    times = {}

    for _, commuter in routes.iterrows():

        commuter_id = commuter["commuter_id"]

        route = commuter.get("route", [])

        if not isinstance(route, (list, tuple)) or not route:
            continue

        # Preferred: use the exact selected edge travel times.
        edges = commuter.get("edges", [])

        if isinstance(edges, list) and edges:

            total_time = sum(
                float(edge.get("travel_time", 0))
                for edge in edges
            )

        else:
            # Fallback for older route DataFrames.
            total_time = commuter.get(
                "travel_time",
                None
            )

            if total_time is None:
                continue

            try:
                total_time = float(total_time)
            except (TypeError, ValueError):
                continue

        if math.isfinite(total_time):
            times[commuter_id] = total_time

    return times


def run_scenario(
    city,
    commuters,
    events=None,
    simulation_hours=3,
    iterations=3
):
    """
    Run one independent scenario.

    The supplied city is copied before any modification.
    """

    scenario_city = deepcopy(city)

    initialise_road_attributes(scenario_city)

    applied_segments = 0

    for event in events or []:
        applied_segments += apply_event(
            scenario_city,
            event
        )

    results = run_congestion_simulation(
        city=scenario_city,
        commuters=commuters,
        simulation_hours=simulation_hours,
        iterations=iterations
    )

    results["scenario_city"] = scenario_city
    results["events_applied"] = len(events or [])
    results["affected_road_segments"] = applied_segments

    results["commuter_times"] = get_commuter_times(
        results["final_routes"]
    )

    return results


def run_simulation(
    city,
    commuters,
    simulation_hours=3,
    iterations=3,
    events=None
):
    """
    Compare baseline traffic against a disrupted scenario.

    The original city is never modified.

    Baseline and disrupted scenarios each receive
    their own independent graph copy.
    """

    events = events or []

    # Baseline: no accidents, floods or closures.
    baseline = run_scenario(
        city=city,
        commuters=commuters,
        events=[],
        simulation_hours=simulation_hours,
        iterations=iterations
    )

    # Disrupted scenario: apply only the specified events.
    disrupted = run_scenario(
        city=city,
        commuters=commuters,
        events=events,
        simulation_hours=simulation_hours,
        iterations=iterations
    )

    baseline_routes = baseline["final_routes"]
    final_routes = disrupted["final_routes"]

    baseline_times = baseline["commuter_times"]
    disrupted_times = disrupted["commuter_times"]

    baseline_route_map = dict(
        zip(
            baseline_routes["commuter_id"],
            baseline_routes["route"]
        )
    )

    final_route_map = dict(
        zip(
            final_routes["commuter_id"],
            final_routes["route"]
        )
    )

    # Count commuters whose routes changed.
    changed_routes = sum(
        baseline_route_map.get(commuter_id)
        != final_route_map.get(commuter_id)

        for commuter_id in baseline_route_map
    )

    common_commuters = (
        set(baseline_times)
        & set(disrupted_times)
    )

    extra_times = [
        disrupted_times[cid] - baseline_times[cid]
        for cid in common_commuters
    ]

    average_baseline_time = (
        sum(baseline_times.values()) / len(baseline_times)
        if baseline_times else 0.0
    )

    average_disrupted_time = (
        sum(disrupted_times.values()) / len(disrupted_times)
        if disrupted_times else 0.0
    )

    average_extra_time = (
        sum(extra_times) / len(extra_times)
        if extra_times else 0.0
    )

    total_commuters = len(commuters)

    reachable = len(disrupted_times)

    unreachable = total_commuters - reachable

    final_traffic = disrupted["final_traffic"]

    average_utilisation = (
        float(final_traffic["utilisation"].mean())
        if not final_traffic.empty else 0.0
    )

    return {

        "commuters": commuters,

        "baseline_routes": baseline_routes,

        "final_routes": final_routes,

        "baseline_traffic": baseline["final_traffic"],

        "final_traffic": final_traffic,

        "baseline_city": baseline["scenario_city"],

        "disrupted_city": disrupted["scenario_city"],

        "summary": {

            "total_commuters": total_commuters,

            "reachable_commuters": reachable,

            "unreachable_commuters": unreachable,

            "affected_commuters": int(changed_routes),

            "changed_routes": int(changed_routes),

            "baseline_average_commute_time": float(
                average_baseline_time
            ),

            "average_commute_time": float(
                average_disrupted_time
            ),

            "average_extra_time": float(
                average_extra_time
            ),

            "average_road_utilisation": average_utilisation,

            "events_applied": len(events),

            "affected_road_segments": (
                disrupted["affected_road_segments"]
            )

        }
    }