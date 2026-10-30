"""
NovaCity - City Event Management

Handles:
1. Road closures
2. Road accidents
3. Flood events
"""

def _get_road(event):
    """Extract and normalize the road from an event."""
    road = event.get("road")

    if not road or len(road) != 2:
        raise ValueError(f"Invalid road in event: {event}")

    return tuple(road)


def apply_road_closure(graph, road):
    """Close a road completely."""

    source, destination = road

    if graph.has_edge(source, destination):
        graph[source][destination]["closed"] = True
        graph[source][destination]["event_factor"] = float("inf")

    return graph


def apply_accident(graph, road):
    """Increase travel time on a road affected by an accident."""

    source, destination = road

    if graph.has_edge(source, destination):
        edge = graph[source][destination]

        edge["event_factor"] = edge.get("event_factor", 1.0) * 3
        edge["travel_time"] = edge.get(
            "travel_time",
            edge.get("distance", 1) / max(edge.get("speed", 1), 0.1)
        ) * 3

        edge["accident"] = True

    return graph


def apply_flood(graph, road):
    """Mark a road as flooded and increase its travel time."""

    source, destination = road

    if graph.has_edge(source, destination):
        edge = graph[source][destination]

        edge["event_factor"] = edge.get("event_factor", 1.0) * 2
        edge["travel_time"] = edge.get(
            "travel_time",
            edge.get("distance", 1) / max(edge.get("speed", 1), 0.1)
        ) * 2

        edge["flooded"] = True

    return graph


def apply_event(graph, event):
    """
    Dispatch an event to the correct event handler.

    Expected format:
    {
        "type": "road_closure",
        "road": ("J1", "J2")
    }
    """

    if not isinstance(event, dict):
        raise TypeError("Event must be provided as a dictionary.")

    event_type = str(event.get("type", "")).lower().strip()
    road = _get_road(event)

    handlers = {
        "road_closure": apply_road_closure,
        "road closure": apply_road_closure,
        "accident": apply_accident,
        "flood": apply_flood,
    }

    handler = handlers.get(event_type)

    if handler is None:
        raise ValueError(f"Unknown event type: {event_type}")

    return handler(graph, road)