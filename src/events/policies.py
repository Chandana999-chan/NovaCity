def apply_bus_policy(bus_frequency):
    """
    Calculate the public transport improvement factor.

    bus_frequency:
        0 = no improvement
        5 = maximum supported improvement

    Returns a multiplier between 0.70 and 1.0.
    """
    if not isinstance(bus_frequency, (int, float)):
        raise TypeError("Bus frequency must be a number.")

    if bus_frequency < 0:
        raise ValueError("Bus frequency cannot be negative.")

    improvement = min(bus_frequency * 0.05, 0.30)
    return 1.0 - improvement


def apply_traffic_policy(traffic_level):
    """
    Calculate the traffic-management improvement factor.

    traffic_level:
        0 = no improvement
        5 = maximum supported improvement

    Returns a multiplier between 0.75 and 1.0.
    """
    if not isinstance(traffic_level, (int, float)):
        raise TypeError("Traffic level must be a number.")

    if traffic_level < 0:
        raise ValueError("Traffic level cannot be negative.")

    reduction = min(traffic_level * 0.05, 0.25)
    return 1.0 - reduction