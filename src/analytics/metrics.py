
import networkx as nx


def calculate_metrics(graph, commuters, bus_factor=1.0, baseline_metrics=None):
    """
    Calculate advanced smart-city performance metrics.

    Road congestion is estimated from commuter route demand
    divided by road capacity. It is a simulation estimate,
    not real-world sensor data.
    """

    bus_factor = max(0.01, float(bus_factor))

    # --------------------------------
    # 1. BUILD ACTIVE ROAD NETWORK
    # --------------------------------

    active_graph = nx.Graph()
    active_graph.add_nodes_from(graph.nodes(data=True))

    for u, v, data in graph.edges(data=True):
        if not data.get("closed", False):
            active_graph.add_edge(
                u,
                v,
                weight=float(data.get("travel_time", 1))
            )

    # --------------------------------
    # 2. COMMUTER ROUTE ANALYSIS
    # --------------------------------

    travel_times = []
    affected = 0
    successful_routes = 0
    routes = []

    # Number of commuter journeys using each road
    edge_flow = {
        frozenset((u, v)): 0
        for u, v in graph.edges()
    }

    for origin, destination in commuters:

        try:
            path = nx.shortest_path(
                active_graph,
                source=origin,
                target=destination,
                weight="weight"
            )

            raw_time = sum(
                active_graph[u][v]["weight"]
                for u, v in zip(path, path[1:])
            )

            final_time = raw_time * bus_factor

            travel_times.append(final_time)
            successful_routes += 1

            # Track road demand
            for u, v in zip(path, path[1:]):
                edge_flow[frozenset((u, v))] += 1

            routes.append({
                "origin": origin,
                "destination": destination,
                "route": " -> ".join(path),
                "travel_time": round(final_time, 2),
                "status": "Connected"
            })

        except (nx.NetworkXNoPath, nx.NodeNotFound):

            affected += 1

            routes.append({
                "origin": origin,
                "destination": destination,
                "route": "No available route",
                "travel_time": None,
                "status": "Disconnected"
            })

    total_commuters = len(commuters)

    average_time = (
        sum(travel_times) / len(travel_times)
        if travel_times else 0
    )

    total_travel_time = sum(travel_times)

    # --------------------------------
    # 3. COMMUTER PERFORMANCE
    # --------------------------------

    route_success_rate = (
        successful_routes / total_commuters * 100
        if total_commuters else 0
    )

    baseline_average = (
        baseline_metrics.get("average_travel_time", average_time)
        if baseline_metrics else average_time
    )

    average_delay = max(0, average_time - baseline_average)

    delay_percentage = (
        average_delay / baseline_average * 100
        if baseline_average > 0 else 0
    )

    # --------------------------------
    # 4. ROAD CONGESTION ANALYSIS
    # --------------------------------

    road_metrics = []

    for u, v, data in graph.edges(data=True):

        closed = data.get("closed", False)
        flow = edge_flow.get(frozenset((u, v)), 0)

        capacity = max(
            1,
            float(data.get("capacity", 4))
        )

        utilization = min(100, (flow / capacity) * 100)

        if closed:
            congestion = 100
            status = "Closed"
        else:
            congestion = utilization

            if congestion >= 85:
                status = "Severe"
            elif congestion >= 60:
                status = "High"
            elif congestion >= 30:
                status = "Moderate"
            else:
                status = "Low"

        road_metrics.append({
            "road": f"{u} - {v}",
            "source": u,
            "destination": v,
            "travel_time": data.get("travel_time", 0),
            "commuter_flow": flow,
            "capacity": capacity,
            "utilization": round(utilization, 2),
            "congestion": round(congestion, 2),
            "status": status,
            "closed": closed
        })

    # --------------------------------
    # 5. BOTTLENECK DETECTION
    # --------------------------------

    bottlenecks = sorted(
        [
            road for road in road_metrics
            if not road["closed"]
        ],
        key=lambda road: (
            road["congestion"],
            road["commuter_flow"]
        ),
        reverse=True
    )

    critical_roads = [
        road for road in bottlenecks
        if road["status"] in ("High", "Severe")
    ]

    # --------------------------------
    # 6. HOSPITAL ACCESSIBILITY
    # --------------------------------

    hospital_name = "Hospital"

    hospital_times = []
    reachable_locations = 0

    if hospital_name in active_graph:

        for node in active_graph.nodes:

            if node == hospital_name:
                hospital_times.append(0)
                reachable_locations += 1
                continue

            try:
                time = nx.shortest_path_length(
                    active_graph,
                    source=node,
                    target=hospital_name,
                    weight="weight"
                )

                hospital_times.append(time)
                reachable_locations += 1

            except nx.NetworkXNoPath:
                pass

    total_locations = active_graph.number_of_nodes()

    hospital_accessibility = (
        reachable_locations / total_locations * 100
        if total_locations else 0
    )

    average_hospital_time = (
        sum(hospital_times) / len(hospital_times)
        if hospital_times else 0
    )

    # --------------------------------
    # 7. CITY HEALTH SCORE
    # --------------------------------

    average_congestion = (
        sum(r["congestion"] for r in road_metrics)
        / len(road_metrics)
        if road_metrics else 0
    )

    congestion_score = max(0, 100 - average_congestion)

    city_health_score = (
        route_success_rate * 0.45
        + hospital_accessibility * 0.35
        + congestion_score * 0.20
    )

    # --------------------------------
    # 8. NETWORK CONNECTIVITY
    # --------------------------------

    components = nx.number_connected_components(active_graph)

    # --------------------------------
    # 9. RETURN ALL ANALYTICS
    # --------------------------------

    return {
        # Existing dashboard metrics
        "average_travel_time": round(average_time, 2),
        "affected_commuters": affected,
        "successful_routes": successful_routes,
        "total_commuters": total_commuters,
        "routes": routes,
        "network_connectivity": components,

        # New commuter analytics
        "total_travel_time": round(total_travel_time, 2),
        "route_success_rate": round(route_success_rate, 2),
        "average_delay": round(average_delay, 2),
        "delay_percentage": round(delay_percentage, 2),

        # New road analytics
        "road_metrics": road_metrics,
        "average_congestion": round(average_congestion, 2),
        "critical_roads": critical_roads,
        "closed_roads": sum(
            1 for road in road_metrics if road["closed"]
        ),

        # Hospital analytics
        "hospital_accessibility": round(
            hospital_accessibility, 2
        ),
        "average_hospital_time": round(
            average_hospital_time, 2
        ),
        "reachable_locations": reachable_locations,

        # City intelligence
        "congestion_score": round(congestion_score, 2),
        "city_health_score": round(city_health_score, 2)
    }
