
def _record_event(data, event_type, severity, factor=1.0):
    """Store event information and accumulate its travel-time effect."""

    data["active_events"] = data.get("active_events", [])

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

    if graph.has_edge(source, destination):
        data = graph[source][destination]

        data["closed"] = True

        _record_event(
            data,
            event_type="road_closure",
            severity="complete"
        )

    return graph


def apply_accident(graph, road, severity="severe"):
    """
    Apply an accident with configurable severity.

    Severity:
        mild     -> 1.5x travel time
        moderate -> 2.0x travel time
        severe   -> 3.0x travel time
    """

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

    if graph.has_edge(source, destination):
        data = graph[source][destination]

        _record_event(
            data,
            event_type="accident",
            severity=severity,
            factor=severity_factors[severity]
        )

    return graph


def apply_flood(graph, road, severity="moderate"):
    """
    Apply partial or complete flooding.

    Severity:
        mild     -> 1.5x travel time
        moderate -> 2.0x travel time
        severe   -> 3.0x travel time
        complete -> road becomes inaccessible
    """

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

    if graph.has_edge(source, destination):
        data = graph[source][destination]

        data["flooded"] = True

        if severity == "complete":
            data["closed"] = True

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
