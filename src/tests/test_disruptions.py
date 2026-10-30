from src.city.city import create_city
from src.simulation.commuters import generate_commuters
from src.simulation.disruptions import analyze_road_closure


def test_road_closure_changes_routes():
    city = create_city()
    commuters = generate_commuters(city, num_commuters=500)

    report = analyze_road_closure(
        city, commuters, ("J10", "J11")
    )

    assert report["changed_routes"] > 0
    assert report["unreachable_commuters"] == 0


def test_road_status_is_restored():
    city = create_city()
    commuters = generate_commuters(city, num_commuters=100)

    analyze_road_closure(
        city, commuters, ("J10", "J11")
    )

    assert city.edges["J10", "J11"]["closed"] is False