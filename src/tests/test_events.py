import networkx as nx

from src.events.events import (
    apply_road_closure,
    apply_accident,
    apply_flood
)


def create_test_graph():
    graph = nx.Graph()

    graph.add_edge(
        "A", "B",
        travel_time=10,
        closed=False
    )

    return graph


def test_road_closure():
    graph = create_test_graph()

    apply_road_closure(graph, ("A", "B"))

    assert graph["A"]["B"]["closed"] is True


def test_accident():
    graph = create_test_graph()

    apply_accident(graph, ("A", "B"))

    assert graph["A"]["B"]["travel_time"] == 30


def test_flood():
    graph = create_test_graph()

    apply_flood(graph, ("A", "B"))

    assert graph["A"]["B"]["travel_time"] == 20
    assert graph["A"]["B"]["flooded"] is True