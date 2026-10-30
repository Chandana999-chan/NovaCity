def apply_road_closure(graph, road):
    source, destination = road

    if graph.has_edge(source, destination):
        graph[source][destination]["closed"] = True

    return graph


def apply_accident(graph, road):
    source, destination = road

    if graph.has_edge(source, destination):
        graph[source][destination]["travel_time"] *= 3

    return graph


def apply_flood(graph, road):
    source, destination = road

    if graph.has_edge(source, destination):
        graph[source][destination]["travel_time"] *= 2
        graph[source][destination]["flooded"] = True

    return graph