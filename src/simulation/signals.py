import random


SIGNAL_CYCLE = {
    "GREEN": 35,
    "YELLOW": 5,
    "RED": 30
}

SIGNAL_STATES = ["GREEN", "YELLOW", "RED"]


def initialise_signals(graph, signal_percentage=0.12, seed=42):
    """Install simulated traffic signals at selected intersections."""

    random.seed(seed)

    intersections = [
        node
        for node, degree in graph.degree()
        if degree >= 3
    ]

    random.shuffle(intersections)

    signal_count = max(
        1,
        int(len(intersections) * signal_percentage)
    )

    selected = set(intersections[:signal_count])

    for node in graph.nodes:

        attributes = graph.nodes[node]

        if node not in selected:
            attributes.update({
                "signalized": False,
                "state": "NONE",
                "timer": 0,
                "cycle_offset": 0
            })
            continue

        offset = random.randint(
            0,
            sum(SIGNAL_CYCLE.values()) - 1
        )

        attributes.update({
            "signalized": True,
            "state": get_signal_state(offset),
            "timer": offset,
            "cycle_offset": offset,
            "red_queue": 0,
            "signal_vehicle_count": 0
        })

    return graph


def get_signal_state(elapsed_seconds):
    """Determine signal state from elapsed cycle time."""

    cycle_length = sum(SIGNAL_CYCLE.values())

    position = elapsed_seconds % cycle_length

    if position < SIGNAL_CYCLE["GREEN"]:
        return "GREEN"

    position -= SIGNAL_CYCLE["GREEN"]

    if position < SIGNAL_CYCLE["YELLOW"]:
        return "YELLOW"

    return "RED"


def update_signals(graph, elapsed_seconds=1):
    """Advance all signal timers."""

    for node, attributes in graph.nodes(data=True):

        if not attributes.get("signalized", False):
            continue

        attributes["timer"] += elapsed_seconds

        attributes["state"] = get_signal_state(
            attributes["timer"]
        )

    return get_signal_statistics(graph)


def set_signal_state(graph, node, state):
    """Manually override a traffic signal."""

    state = state.upper()

    if state not in SIGNAL_STATES:
        raise ValueError(
            "Signal state must be GREEN, YELLOW or RED"
        )

    if node not in graph:
        raise ValueError("Intersection does not exist")

    if not graph.nodes[node].get("signalized", False):
        raise ValueError("No traffic signal at this intersection")

    graph.nodes[node]["state"] = state


def get_signal_statistics(graph):
    """Return current traffic signal statistics."""

    statistics = {
        "total_signals": 0,
        "green": 0,
        "yellow": 0,
        "red": 0
    }

    for _, attributes in graph.nodes(data=True):

        if not attributes.get("signalized", False):
            continue

        statistics["total_signals"] += 1

        state = attributes.get("state", "RED").lower()

        if state in statistics:
            statistics[state] += 1

    return statistics