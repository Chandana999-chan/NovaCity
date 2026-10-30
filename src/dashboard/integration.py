from src.city.city import load_real_city
from src.simulation.commuters import generate_commuters
from src.simulation.engine import run_simulation


def create_sample_city():
    """
    Load the actual OpenStreetMap road network
    around K.R. Market, Bengaluru.
    """
    return load_real_city()


def create_sample_commuters(city, num_commuters=500):
    """
    Generate commuters using actual road-network nodes.
    """
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
    Run the NovaCity baseline and disrupted scenarios.

    Each scenario gets an independent graph copy.
    """

    return run_simulation(
        city=city,
        commuters=commuters,
        events=events or [],
        simulation_hours=simulation_hours,
        iterations=iterations
    )


def calculate_metrics(graph, commuters, events=None):
    """
    Calculate dashboard metrics using actual simulation results.
    """

    results = run_dashboard_simulation(
        city=graph,
        commuters=commuters,
        events=events
    )

    summary = results["summary"]

    return {
        "average_travel_time": summary["average_commute_time"],
        "baseline_average_travel_time": summary[
            "baseline_average_commute_time"
        ],
        "average_extra_time": summary["average_extra_time"],
        "affected_commuters": summary["affected_commuters"],
        "successful_routes": summary["reachable_commuters"],
        "unreachable_commuters": summary["unreachable_commuters"],
        "total_commuters": summary["total_commuters"],
        "changed_routes": summary["changed_routes"],
        "average_road_utilisation": summary[
            "average_road_utilisation"
        ],
        "events_applied": summary["events_applied"],
        "affected_road_segments": summary[
            "affected_road_segments"
        ],
        "routes": results["final_routes"].to_dict("records"),
        "baseline_routes": results["baseline_routes"].to_dict("records"),
        "network_connectivity": summary["reachable_commuters"],
        "simulation_results": results
    }