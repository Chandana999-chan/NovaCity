"""
NovaCity dashboard integration.

Connects the dashboard with the actual city and simulation engine.
"""

from src.city.city import create_city
from src.simulation.commuters import generate_commuters
from src.simulation.engine import run_simulation


def create_sample_city():
    """Create the NovaCity road network."""
    return create_city()


def create_sample_commuters(city, num_commuters=500):
    """Generate commuters for the city."""
    return generate_commuters(
        city,
        num_commuters=num_commuters
    )


def run_dashboard_simulation(
    city,
    commuters,
    events=None,
    simulation_hours=3,
    iterations=3
):
    """
    Run baseline and disrupted city simulations.

    Uses positional graph argument for compatibility
    with the current simulation engine.
    """

    return run_simulation(
        city,
        commuters,
        simulation_hours=simulation_hours,
        iterations=iterations,
        events=events or []
    )


def calculate_metrics(graph, commuters, events=None):
    """Return dashboard-compatible metrics."""

    results = run_dashboard_simulation(
        graph,
        commuters,
        events=events
    )

    summary = results["summary"]
    disrupted = results["disrupted"]

    return {
        "average_travel_time": summary.get(
            "disrupted_average_time", 0
        ),
        "average_extra_time": summary.get(
            "average_extra_time", 0
        ),
        "affected_commuters": summary.get(
            "delayed_commuters", 0
        ),
        "successful_routes": summary.get(
            "reachable_commuters", 0
        ),
        "total_commuters": summary.get(
            "total_commuters", 0
        ),
        "routes": disrupted["final_routes"].to_dict(
            orient="records"
        ),
        "network_connectivity": summary.get(
            "reachable_commuters", 0
        ),
        "changed_routes": summary.get(
            "changed_routes", 0
        )
    }