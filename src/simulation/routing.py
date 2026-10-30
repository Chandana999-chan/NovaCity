
import networkx as nx
import pandas as pd


def calculate_route(city, origin, destination, weight="travel_time"):

    if origin not in city or destination not in city:
        raise ValueError("Origin or destination does not exist.")

    # Exclude closed roads
    available_city = nx.subgraph_view(
        city,
        filter_edge=lambda u, v: not city.edges[u, v].get(
            "closed", False
        )
    )

    try:
        route = nx.shortest_path(
            available_city,
            source=origin,
            target=destination,
            weight=weight
        )

        route_distance = sum(
            city.edges[u, v]["distance"]
            for u, v in zip(route[:-1], route[1:])
        )

        return {
            "route": route,
            "distance": route_distance
        }

    except nx.NetworkXNoPath:
        return {
            "route": [],
            "distance": None
        }


def calculate_all_routes(city, commuters):

    results = []

    for _, commuter in commuters.iterrows():

        result = calculate_route(
            city,
            commuter["origin"],
            commuter["destination"],
            weight="travel_time"
        )

        results.append({
            "commuter_id": commuter["commuter_id"],
            "origin": commuter["origin"],
            "destination": commuter["destination"],
            "route": result["route"],
            "distance": result["distance"],
            "transport_mode": commuter["transport_mode"]
        })

    return pd.DataFrame(results)


if __name__ == "__main__":

    from src.city.city import create_city
    from src.simulation.commuters import generate_commuters

    city = create_city()

    # Initial free-flow travel time in minutes
    for u, v, data in city.edges(data=True):
        data["travel_time"] = (
            data["distance"] / data["speed"]
        ) * 60

    commuters = generate_commuters(city)

    routes = calculate_all_routes(city, commuters)

    print("NOVACITY ROUTING ENGINE")
    print("-----------------------")

    print("Total commuters:", len(routes))
    print("Successful routes:", (routes["distance"].notna()).sum())
    print("Failed routes:", routes["distance"].isna().sum())

    print("\nSample routes:")

    print(
        routes[
            ["commuter_id", "origin", "destination", "route", "distance"]
        ].head(10).to_string(index=False)
    )
