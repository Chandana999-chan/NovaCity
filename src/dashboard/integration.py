
from src.city.city import create_city
from src.simulation.commuters import generate_commuters
from src.simulation.engine import run_simulation


def create_sample_city():
    """Compatibility wrapper for Member 2's dashboard."""
    return create_city()


def create_sample_commuters(city, num_commuters=500):
    """Generate commuters using the actual simulation model."""
    return generate_commuters(city, num_commuters=num_commuters)


def calculate_metrics(graph, commuters, events=None):
    """Adapt the simulation engine output to dashboard metrics."""

    results = run_simulation(
        city=graph,
        commuters=commuters,
        events=events or []
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
def run_dashboard_simulation(city, commuters, events=None):
    """Run baseline and scenario together for the dashboard."""
    return run_simulation(
        city=city,
        commuters=commuters,
        events=events or []
    )