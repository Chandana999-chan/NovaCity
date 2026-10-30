
def apply_road_closure(graph, road):
    source, destination = road

    if graph.has_edge(source, destination):
        graph[source][destination]["closed"] = True

    return graph


def apply_accident(graph, road):
    source, destination = road

    if graph.has_edge(source, destination):
        data = graph[source][destination]

        data["event_factor"] = (
            data.get("event_factor", 1.0) * 3
        )
        data["travel_time"] *= 3

    return graph


def apply_flood(graph, road):
    source, destination = road

    if graph.has_edge(source, destination):
        data = graph[source][destination]

        data["event_factor"] = (
            data.get("event_factor", 1.0) * 2
        )
        data["travel_time"] *= 2
        data["flooded"] = True

    return graph
