
import networkx as nx
import pandas as pd

from src.city.city import create_city
from src.simulation.commuters import generate_commuters
from src.simulation.routing import calculate_all_routes


def calculate_traffic(city, routes, simulation_hours=3):
    """
    Calculate traffic volume, road utilisation and congestion-adjusted
    travel time for every road in the city.

    Assumptions:
    - Each car commuter represents one car.
    - Bus commuters are counted as passengers, not separate vehicles.
    - Traffic is averaged over the simulation period.
    - Road capacity is measured in vehicles per hour.
    """

    if simulation_hours <= 0:
        raise ValueError("Simulation hours must be positive.")

    if routes.empty:
        raise ValueError("Route data is empty.")

    # Step 1: Initialise traffic counts for every road.
    # Sorting ensures both directions of an undirected road
    # use the same dictionary key.

    road_counts = {}

    for u, v, data in city.edges(data=True):
        key = tuple(sorted((u, v)))

        road_counts[key] = {
            "car_traversals": 0,
            "bus_passengers": 0
        }

    # Step 2: Count commuter movements on each road.

    for _, commuter in routes.iterrows():

        route = commuter["route"]
        transport_mode = commuter["transport_mode"]

        if not route:
            continue

        for u, v in zip(route[:-1], route[1:]):

            if not city.has_edge(u, v):
                continue

            key = tuple(sorted((u, v)))

            if key not in road_counts:
                continue

            if transport_mode == "car":
                road_counts[key]["car_traversals"] += 1

            elif transport_mode == "bus":
                road_counts[key]["bus_passengers"] += 1

    # Step 3: Calculate road utilisation and travel time.

    road_results = []

    for (u, v), counts in road_counts.items():

        data = city.edges[u, v]

        car_traversals = counts["car_traversals"]
        bus_passengers = counts["bus_passengers"]

        # Average car vehicles per hour.
        vehicles_per_hour = car_traversals / simulation_hours

        capacity = data["capacity"]

        # Road utilisation as a fraction.
        utilisation_ratio = vehicles_per_hour / capacity

        # Road utilisation as a percentage.
        utilisation_percent = utilisation_ratio * 100

        # Free-flow travel time in minutes.
        free_flow_time = (
            data["distance"] / data["speed"]
        ) * 60

        # Simplified BPR-style congestion model.
        congestion_factor = (
            1 + 0.15 * (utilisation_ratio ** 4)
        )

        event_factor = data.get("event_factor", 1.0)

        travel_time = (
            free_flow_time
            * congestion_factor
            * event_factor
        )

        # Update graph edge attributes.
        data["traffic"] = vehicles_per_hour
        data["utilisation"] = utilisation_ratio
        data["travel_time"] = travel_time

        # Store results.
        road_results.append({
            "road": f"{u}-{v}",
            "start": u,
            "end": v,
            "car_traversals": car_traversals,
            "bus_passengers": bus_passengers,
            "vehicles_per_hour": round(vehicles_per_hour, 2),
            "capacity": capacity,
            "utilisation": round(utilisation_percent, 2),
            "free_flow_time": round(free_flow_time, 3),
            "travel_time": round(travel_time, 3)
        })

    return pd.DataFrame(road_results)


def run_congestion_simulation(city, commuters, simulation_hours=3, iterations=3):
    """
    Run an iterative traffic simulation.
    Routes are recalculated using congestion-adjusted travel times.
    """

    if iterations < 1:
        raise ValueError("Iterations must be at least 1.")

    # Initialise all roads with free-flow travel times.
    for u, v, data in city.edges(data=True):
        free_flow_time = (
        data["distance"] / data["speed"]
        ) * 60

        event_factor = data.get("event_factor", 1.0)

        data["travel_time"] = free_flow_time * event_factor

    # Baseline: routes before congestion is considered.
    baseline_routes = calculate_all_routes(city, commuters)

    baseline_traffic = calculate_traffic(
        city, baseline_routes, simulation_hours
    )

    current_routes = baseline_routes
    current_traffic = baseline_traffic

    # Iteratively recalculate routes using updated road times.
    for iteration in range(iterations):

        print(f"\nSimulation iteration: {iteration + 1}/{iterations}")

        current_routes = calculate_all_routes(city, commuters)

        current_traffic = calculate_traffic(
            city, current_routes, simulation_hours
        )

    # Count commuters whose routes changed.
    changed_routes = sum(
        1
        for old_route, new_route in zip(
            baseline_routes["route"],
            current_routes["route"]
        )
        if old_route != new_route
    )

    return {
        "baseline_routes": baseline_routes,
        "final_routes": current_routes,
        "baseline_traffic": baseline_traffic,
        "final_traffic": current_traffic,
        "changed_routes": changed_routes
    }



if __name__ == "__main__":

    print("\nNOVACITY CONGESTION-AWARE SIMULATION")
    print("------------------------------------")

    city = create_city()

    commuters = generate_commuters(
        city,
        num_commuters=500
    )

    results = run_congestion_simulation(
        city,
        commuters,
        simulation_hours=3,
        iterations=3
    )

    final_traffic = results["final_traffic"]

    print("\nSIMULATION RESULTS")
    print("------------------")

    print("Total commuters:", len(commuters))
    print("Roads analysed:", len(final_traffic))

    print(
        "Commuters with changed routes:",
        results["changed_routes"]
    )

    print("\nTop 10 busiest roads:")

    busiest = final_traffic.sort_values(
        by="vehicles_per_hour",
        ascending=False
    )

    print(
        busiest[
            [
                "road",
                "vehicles_per_hour",
                "capacity",
                "utilisation",
                "travel_time"
            ]
        ].head(10).to_string(index=False)
    )

    print(
        "\nAverage road utilisation:",
        round(final_traffic["utilisation"].mean(), 2),
        "%"
    )

    print(
        "Average road travel time:",
        round(final_traffic["travel_time"].mean(), 3),
        "minutes"
    )

    print("\nCongestion-aware simulation completed!")
