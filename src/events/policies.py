def apply_bus_policy(bus_frequency):
    """
    Higher bus frequency reduces estimated
    public transport waiting time.
    """
    improvement = min(bus_frequency * 0.05, 0.30)

    return 1 - improvement


def apply_traffic_policy(traffic_level):
    """
    Simulates traffic management improvements.
    """
    reduction = min(traffic_level * 0.05, 0.25)

    return 1 - reduction