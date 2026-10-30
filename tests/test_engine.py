
from src.city.city import create_city
from src.simulation.commuters import generate_commuters
from src.simulation.engine import run_simulation


def test_simulation_engine():
    city = create_city()
    commuters = generate_commuters(city, num_commuters=100)

    result = run_simulation(city, commuters)

    assert result["summary"]["total_commuters"] == 100
    assert result["summary"]["reachable_commuters"] > 0
    assert "final_routes" in result
    assert "final_traffic" in result


def test_simulation_summary_types():
    city = create_city()
    commuters = generate_commuters(city, num_commuters=50)

    result = run_simulation(city, commuters)
    summary = result["summary"]

    assert isinstance(summary["average_commute_time"], float)
    assert isinstance(summary["average_road_utilisation"], float)


def test_accident_event_integration():
    city = create_city()
    commuters = generate_commuters(city, num_commuters=100)

    events = [
        {"type": "accident", "road": ("J10", "J11")}
    ]

    result = run_simulation(city, commuters, events=events)

    assert result["summary"]["events_applied"] == 1
    assert result["summary"]["reachable_commuters"] > 0


def test_original_city_is_not_modified():
    city = create_city()
    commuters = generate_commuters(city, num_commuters=50)

    original_closed = city.edges["J10", "J11"]["closed"]
    original_factor = city.edges["J10", "J11"].get("event_factor", 1.0)

    events = [
        {"type": "accident", "road": ("J10", "J11")}
    ]

    run_simulation(city, commuters, events=events)

    assert city.edges["J10", "J11"]["closed"] == original_closed
    assert city.edges["J10", "J11"].get("event_factor", 1.0) == original_factor
