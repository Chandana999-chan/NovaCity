
from copy import deepcopy

from src.events.events import (
    apply_road_closure,
    apply_accident,
    apply_flood
)
from src.simulation.traffic import run_congestion_simulation


def _get_commuter_times(city, routes):
    times = {}

    for _, commuter in routes.iterrows():
        route = commuter["route"]

        if not route:
            continue

        total_time = sum(
            city.edges[u, v]["travel_time"]
            for u, v in zip(route[:-1], route[1:])
        )

        times[commuter["commuter_id"]] = float(total_time)

    return times


def run_simulation(
    city,
    commuters,
    simulation_hours=3,
    iterations=3,
    events=None
):
    events = events or []

    baseline_city = deepcopy(city)
    disrupted_city = deepcopy(city)

    for _, _, data in disrupted_city.edges(data=True):
        data["event_factor"] = data.get("event_factor", 1.0)
        data["travel_time"] = (
            data["distance"] / data["speed"]
        ) * 60

    event_functions = {
        "road_closure": apply_road_closure,
        "accident": apply_accident,
        "flood": apply_flood
    }

    for event in events:
        event_type = event.get("type")
        road = event.get("road")

        if event_type not in event_functions:
            raise ValueError(f"Unsupported event type: {event_type}")

        if not isinstance(road, (tuple, list)) or len(road) != 2:
            raise ValueError("Each event must specify a road with two junctions.")

        if not disrupted_city.has_edge(*road):
            raise ValueError(f"Road does not exist: {road}")

        event_functions[event_type](disrupted_city, tuple(road))

    baseline = run_congestion_simulation(
        baseline_city, commuters, simulation_hours, iterations
    )

    disrupted = run_congestion_simulation(
        disrupted_city, commuters, simulation_hours, iterations
    )

    baseline_routes = baseline["final_routes"]
    final_routes = disrupted["final_routes"]

    baseline_times = _get_commuter_times(
        baseline_city, baseline_routes
    )
    disrupted_times = _get_commuter_times(
        disrupted_city, final_routes
    )

    baseline_route_map = dict(zip(
        baseline_routes["commuter_id"],
        baseline_routes["route"]
    ))

    final_route_map = dict(zip(
        final_routes["commuter_id"],
        final_routes["route"]
    ))

    changed_routes = sum(
        baseline_route_map[cid] != final_route_map[cid]
        for cid in baseline_route_map
    )

    extra_times = [
        disrupted_times[cid] - baseline_times[cid]
        for cid in baseline_times
        if cid in disrupted_times
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

    unreachable = len(commuters) - len(disrupted_times)

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
        "summary": {
            "total_commuters": len(commuters),
            "reachable_commuters": len(disrupted_times),
            "unreachable_commuters": unreachable,
            "affected_commuters": int(changed_routes),
            "changed_routes": int(changed_routes),
            "baseline_average_commute_time": float(average_baseline_time),
            "average_commute_time": float(average_disrupted_time),
            "average_extra_time": float(average_extra_time),
            "average_road_utilisation": average_utilisation,
            "events_applied": len(events)
        }
    }
