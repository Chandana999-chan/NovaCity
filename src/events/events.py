from datetime import datetime
from uuid import uuid4


SUPPORTED_EVENTS = {
    "road_closure",
    "accident",
    "flood"
}


def get_target_edges(graph, road):
    """
    Resolve an event target to actual road segments.

    Supported:
        (u, v)       -> all parallel segments u to v
        (u, v, key)  -> one exact segment
        road_id      -> segment identified by road_id
    """

    targets = []

    if isinstance(road, str):

        for u, v, key, data in graph.edges(
            keys=True,
            data=True
        ):

            if data.get("road_id") == road:
                targets.append((u, v, key))

    elif isinstance(road, (tuple, list)):

        if len(road) == 2:

            u, v = road

            if graph.has_edge(u, v):

                if graph.is_multigraph():

                    for key in graph[u][v]:
                        targets.append((u, v, key))

                else:
                    targets.append((u, v, 0))

        elif len(road) == 3:

            u, v, key = road

            if graph.is_multigraph():

                if graph.has_edge(u, v, key):
                    targets.append((u, v, key))

            elif graph.has_edge(u, v):
                targets.append((u, v, 0))

    if not targets:
        raise ValueError(
            f"Road segment not found: {road}"
        )

    return targets


def create_event(
    event_type,
    road,
    severity="moderate",
    flood_depth=0.0,
    duration_minutes=60
):
    """
    Create an event definition.

    Severity:
        low
        moderate
        high
        critical
    """

    if event_type not in SUPPORTED_EVENTS:
        raise ValueError(
            f"Unsupported event type: {event_type}"
        )

    if severity not in {
        "low",
        "moderate",
        "high",
        "critical"
    }:
        raise ValueError("Invalid event severity.")

    if duration_minutes <= 0:
        raise ValueError(
            "Event duration must be positive."
        )

    if event_type == "flood" and flood_depth < 0:
        raise ValueError(
            "Flood depth cannot be negative."
        )

    return {
        "event_id": str(uuid4())[:8],
        "type": event_type,
        "road": road,
        "severity": severity,
        "flood_depth": float(flood_depth),
        "duration_minutes": int(duration_minutes),
        "created_at": datetime.now().isoformat()
    }


def apply_road_closure(graph, road):
    """
    Close all targeted road segments.
    """

    targets = get_target_edges(graph, road)

    for u, v, key in targets:

        data = graph.edges[u, v, key]

        data["closed"] = True
        data["closure"] = True
        data["event_type"] = "road_closure"

    return graph


def apply_accident(
    graph,
    road,
    severity="moderate"
):
    """
    Simulate an accident by reducing usable road capacity.

    Severity determines the capacity reduction.
    """

    capacity_reduction = {
        "low": 0.15,
        "moderate": 0.30,
        "high": 0.50,
        "critical": 0.80
    }

    if severity not in capacity_reduction:
        raise ValueError("Invalid accident severity.")

    targets = get_target_edges(graph, road)

    for u, v, key in targets:

        data = graph.edges[u, v, key]

        original_capacity = float(
            data.get("original_capacity",
                     data.get("capacity", 600))
        )

        data["original_capacity"] = original_capacity

        reduction = capacity_reduction[severity]

        data["capacity"] = max(
            original_capacity * (1 - reduction),
            1
        )

        data["accident"] = True
        data["accident_severity"] = severity

        data["event_factor"] = max(
            float(data.get("event_factor", 1.0)),
            1.0
        ) * 1.5

    return graph


def apply_flood(
    graph,
    road,
    depth=0.3,
    severity=None
):
    """
    Simulate flooding.

    Depth is measured in metres.

    Water depth:
        0.0 - 0.15 m: minor impact
        0.15 - 0.30 m: moderate impact
        0.30 - 0.50 m: severe impact
        Above 0.50 m: road treated as impassable
    """

    if depth < 0:
        raise ValueError(
            "Flood depth cannot be negative."
        )

    targets = get_target_edges(graph, road)

    for u, v, key in targets:

        data = graph.edges[u, v, key]

        original_capacity = float(
            data.get("original_capacity",
                     data.get("capacity", 600))
        )

        data["original_capacity"] = original_capacity

        if depth < 0.15:
            capacity_factor = 0.85

        elif depth < 0.30:
            capacity_factor = 0.60

        elif depth < 0.50:
            capacity_factor = 0.25

        else:
            capacity_factor = 0.0

        data["flooded"] = True
        data["flood_depth"] = float(depth)

        data["capacity"] = max(
            original_capacity * capacity_factor,
            1
        )

        data["event_factor"] = (
            float(data.get("event_factor", 1.0))
            * (1 + depth * 2)
        )

        # Treat deep flooding as an impassable road.
        if depth >= 0.50:
            data["closed"] = True

    return graph


def apply_event(graph, event):
    """
    Apply one event definition to a scenario graph.
    """

    event_type = event["type"]
    road = event["road"]

    if event_type == "road_closure":

        apply_road_closure(graph, road)

    elif event_type == "accident":

        apply_accident(
            graph,
            road,
            severity=event.get(
                "severity",
                "moderate"
            )
        )

    elif event_type == "flood":

        apply_flood(
            graph,
            road,
            depth=event.get(
                "flood_depth",
                0.3
            )
        )

    return graph