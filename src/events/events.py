"""
NovaCity - City Event Management

Handles:
1. Road closures
2. Road accidents with configurable severity
3. Flood events with configurable severity
"""

import math


def _get_road(event):
    """Extract and validate the road from an event."""
    road = event.get("road")

    if not road or len(road) != 2:
        raise ValueError(f"Invalid road in event: {event}")

    return tuple(road)


def _get_edge_data(graph, source, destination):
    """
    Return edge attribute dictionaries.

    Supports both NetworkX Graph and MultiGraph.
    For MultiGraph, an event affects all parallel edges
    between the selected junctions.
    """
    if not graph.has_edge(source, destination):
        return []

    if graph.is_multigraph():
        return list(graph[source][destination].values())

    return [graph[source][destination]]


def _record_event(data, event_type, severity, factor=1.0):
    """Record an event and accumulate its travel-time effect."""

    data.setdefault("active_events", [])

    data["active_events"].append({
        "type": event_type,
        "severity": severity
    })

    data["event_factor"] = (
        data.get("event_factor", 1.0) * factor
    )

    if "travel_time" in data:
        data["travel_time"] *= factor


def apply_road_closure(graph, road):
    """Completely close a road."""

    source, destination = road

    for data in _get_edge_data(graph, source, destination):
        data["closed"] = True
        data["event_factor"] = math.inf
        data["travel_time"] = math.inf

        _record_event(
            data,
            event_type="road_closure",
            severity="complete"
        )

    return graph


def apply_accident(graph, road, severity="severe"):
    """
    Apply an accident with configurable severity.

    mild     -> 1.5x travel time
    moderate -> 2.0x travel time
    severe   -> 3.0x travel time
    """

    severity = str(severity).lower().strip()

    severity_factors = {
        "mild": 1.5,
        "moderate": 2.0,
        "severe": 3.0
    }

    if severity not in severity_factors:
        raise ValueError(
            "Accident severity must be mild, moderate, or severe."
        )

    source, destination = road

    for data in _get_edge_data(graph, source, destination):
        data["accident"] = True

        _record_event(
            data,
            event_type="accident",
            severity=severity,
            factor=severity_factors[severity]
        )

    return graph


def apply_flood(graph, road, severity="moderate"):
    """
    Apply a flood with configurable severity.

    mild     -> 1.5x travel time
    moderate -> 2.0x travel time
    severe   -> 3.0x travel time
    complete -> road becomes inaccessible
    """

    severity = str(severity).lower().strip()

    severity_factors = {
        "mild": 1.5,
        "moderate": 2.0,
        "severe": 3.0
    }

    valid_severities = [
        "mild",
        "moderate",
        "severe",
        "complete"
    ]

    if severity not in valid_severities:
        raise ValueError(
            "Flood severity must be mild, moderate, severe, or complete."
        )

    source, destination = road

    for data in _get_edge_data(graph, source, destination):
        data["flooded"] = True

        if severity == "complete":
            data["closed"] = True
            data["event_factor"] = math.inf
            data["travel_time"] = math.inf

            _record_event(
                data,
                event_type="flood",
                severity="complete"
            )

        else:
            _record_event(
                data,
                event_type="flood",
                severity=severity,
                factor=severity_factors[severity]
            )

    return graph


def apply_event(graph, event):
    """
    Apply an event to the city network.

    Example:
    {
        "type": "accident",
        "road": ("J1", "J2"),
        "severity": "severe"
    }
    """

    if not isinstance(event, dict):
        raise TypeError("Event must be provided as a dictionary.")

    event_type = str(event.get("type", "")).lower().strip()
    road = _get_road(event)
    severity = event.get("severity")

    if event_type in ("road_closure", "road closure"):
        return apply_road_closure(graph, road)

    if event_type == "accident":
        return apply_accident(
            graph,
            road,
            severity=severity or "severe"
        )

    if event_type == "flood":
        return apply_flood(
            graph,
            road,
            severity=severity or "moderate"
        )

    raise ValueError(f"Unknown event type: {event_type}")