
from src.city.city import create_city
from src.simulation.routing import calculate_route


def test_closed_road_is_not_used():

    city = create_city()

    # Close the main connection between two districts.
    city.edges["J10", "J11"]["closed"] = True

    result = calculate_route(
        city,
        "J1",
        "J15"
    )

    assert result["route"], "Alternative route should exist."

    route = result["route"]

    # Ensure the closed road is not used in either direction.
    for u, v in zip(route[:-1], route[1:]):
        assert not (
            {u, v} == {"J10", "J11"}
        ), "Route incorrectly uses a closed road."

    print("PASS: Closed road avoided successfully.")


def test_no_route_when_all_roads_are_closed():

    city = create_city()

    # Close every road.
    for u, v in city.edges():
        city.edges[u, v]["closed"] = True

    result = calculate_route(
        city,
        "J1",
        "J15"
    )

    assert result["route"] == []
    assert result["distance"] is None

    print("PASS: No route returned when all roads are closed.")
