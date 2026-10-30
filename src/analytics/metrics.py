import networkx as nx


def calculate_metrics(graph, commuters, bus_factor=1.0):
    active_graph = nx.Graph()

    active_graph.add_nodes_from(graph.nodes(data=True))

    for u, v, data in graph.edges(data=True):
        if not data.get("closed", False):
            active_graph.add_edge(
                u,
                v,
                weight=data["travel_time"]
            )

    travel_times = []
    affected = 0
    successful_routes = 0
    routes = []

    for origin, destination in commuters:

        try:
            path = nx.shortest_path(
                active_graph,
                origin,
                destination,
                weight="weight"
            )

            travel_time = nx.shortest_path_length(
                active_graph,
                origin,
                destination,
                weight="weight"
            )

            travel_time *= bus_factor

            travel_times.append(travel_time)
            successful_routes += 1

            routes.append({
                "origin": origin,
                "destination": destination,
                "route": " → ".join(path),
                "travel_time": round(travel_time, 2)
            })

        except nx.NetworkXNoPath:
            affected += 1

            routes.append({
                "origin": origin,
                "destination": destination,
                "route": "No available route",
                "travel_time": None
            })

    average_time = (
        sum(travel_times) / len(travel_times)
        if travel_times else 0
    )

    return {
        "average_travel_time": round(average_time, 2),
        "affected_commuters": affected,
        "successful_routes": successful_routes,
        "total_commuters": len(commuters),
        "routes": routes,
        "network_connectivity": (
            nx.number_connected_components(active_graph)
        )
    }