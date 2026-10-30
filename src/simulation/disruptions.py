
import pandas as pd

from src.simulation.routing import calculate_all_routes


def route_travel_time(city, route):
    """Calculate total route travel time in minutes."""

    total_time = 0.0

    for u, v in zip(route[:-1], route[1:]):
        data = city.edges[u, v]
        total_time += data["travel_time"]

    return total_time


def analyze_road_closure(city, commuters, road):
    """Compare commuter journeys before and after road closure."""

    u, v = road

    if not city.has_edge(u, v):
        raise ValueError(f"Road {u}-{v} does not exist.")

    # Initialise free-flow travel time.
    for a, b, data in city.edges(data=True):
        data["travel_time"] = (
            data["distance"] / data["speed"]
        ) * 60

    # Calculate normal routes.
    normal_routes = calculate_all_routes(city, commuters)

    # Save original road status.
    original_status = city.edges[u, v].get("closed", False)

    try:
        # Close selected road.
        city.edges[u, v]["closed"] = True

        # Calculate routes after closure.
        disrupted_routes = calculate_all_routes(city, commuters)

    finally:
        # Restore original road status.
        city.edges[u, v]["closed"] = original_status

    # Compare routes.
    comparisons = []

    for index in range(len(normal_routes)):

        normal = normal_routes.iloc[index]
        disrupted = disrupted_routes.iloc[index]

        normal_route = normal["route"]
        disrupted_route = disrupted["route"]

        reachable = bool(disrupted_route)

        normal_distance = normal["distance"]
        disrupted_distance = disrupted["distance"]

        normal_time = route_travel_time(city, normal_route)

        disrupted_time = (
            route_travel_time(city, disrupted_route)
            if reachable else None
        )

        comparisons.append({
            "commuter_id": normal["commuter_id"],
            "normal_route": normal_route,
            "disrupted_route": disrupted_route,
            "route_changed": normal_route != disrupted_route,
            "reachable": reachable,
            "normal_distance": normal_distance,
            "disrupted_distance": disrupted_distance,
            "extra_distance": (
                disrupted_distance - normal_distance
                if reachable else None
            ),
            "normal_time": normal_time,
            "disrupted_time": disrupted_time,
            "extra_time": (
                disrupted_time - normal_time
                if reachable else None
            )
        })

    results = pd.DataFrame(comparisons)

    affected = results[
        results["route_changed"] | ~results["reachable"]
    ]

    reachable_results = results[results["reachable"]]

    return {
        "results": results,
        "total_commuters": len(results),
        "affected_commuters": len(affected),
        "changed_routes": int(results["route_changed"].sum()),
        "unreachable_commuters": int((~results["reachable"]).sum()),
        "average_extra_distance": (
            reachable_results["extra_distance"].mean()
            if len(reachable_results) else 0
        ),
        "average_extra_time": (
            reachable_results["extra_time"].mean()
            if len(reachable_results) else 0
        )
    }


if __name__ == "__main__":

    from src.city.city import create_city
    from src.simulation.commuters import generate_commuters

    city = create_city()

    commuters = generate_commuters(
        city,
        num_commuters=500
    )

    report = analyze_road_closure(
        city,
        commuters,
        ("J10", "J11")
    )

    print("\nNOVACITY ROAD CLOSURE IMPACT")
    print("----------------------------")
    print("Closed road: J10-J11")
    print("Total commuters:", report["total_commuters"])
    print("Affected commuters:", report["affected_commuters"])
    print("Changed routes:", report["changed_routes"])
    print("Unreachable commuters:", report["unreachable_commuters"])

    print(
        "Average additional distance:",
        round(report["average_extra_distance"], 2),
        "km"
    )

    print(
        "Average additional travel time:",
        round(report["average_extra_time"], 2),
        "minutes"
    )
