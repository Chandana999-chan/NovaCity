from src.city.city import create_city
from src.simulation.commuters import generate_commuters
from src.simulation.engine import run_simulation


def create_sample_city():
    return create_city()


def create_sample_commuters(city, num_commuters=500):
    return generate_commuters(city, num_commuters=num_commuters)


def run_dashboard_simulation(
    city,
    commuters,
    events=None,
    simulation_hours=3,
    iterations=3
):
    """Run the actual NovaCity simulation."""

    return run_simulation(
        city,  # Positional argument fixes the keyword mismatch
        commuters,
        simulation_hours=simulation_hours,
        iterations=iterations,
        events=events or []
    )


def calculate_metrics(graph, commuters, events=None):
    results = run_dashboard_simulation(
        graph,
        commuters,
        events=events
    )

    summary = results["summary"]

    return {
        "average_travel_time": summary["average_commute_time"],
        "affected_commuters": summary["affected_commuters"],
        "successful_routes": summary["reachable_commuters"],
        "total_commuters": summary["total_commuters"],
        "routes": results["final_routes"].to_dict("records"),
        "network_connectivity": summary["reachable_commuters"]
    }