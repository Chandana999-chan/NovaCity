import os
import pickle
from pathlib import Path

import networkx as nx
import osmnx as ox


# --------------------------------------------------
# NOVACITY - REAL BENGALURU MAP
# --------------------------------------------------

CITY_NAME = "KR Market, Bengaluru, Karnataka, India"

MAP_DISTANCE = 1200

CACHE_DIR = Path("data/osm")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

GRAPH_FILE = CACHE_DIR / "kr_market_drive.graphml"


def download_real_city():

    """
    Download the real driving road network around
    KR Market, Bengaluru, using OpenStreetMap.
    """

    ox.settings.use_cache = True
    ox.settings.log_console = True
    ox.settings.timeout = 180

    print("\nDownloading real Bengaluru road network...")

    graph = ox.graph.graph_from_address(
        CITY_NAME,
        dist=MAP_DISTANCE,
        network_type="drive",
        simplify=True,
        retain_all=False,
    )

    graph = ox.add_edge_speeds(graph)
    graph = ox.add_edge_travel_times(graph)

    ox.save_graphml(graph, GRAPH_FILE)

    print("Real road network downloaded.")
    print("Junctions:", graph.number_of_nodes())
    print("Road segments:", graph.number_of_edges())

    return graph


def load_real_city(force_download=False):

    """
    Load the cached OpenStreetMap network.
    Download it if no cached network exists.
    """

    if GRAPH_FILE.exists() and not force_download:

        print("Loading cached Bengaluru road network...")

        graph = ox.load_graphml(GRAPH_FILE)

    else:

        graph = download_real_city()

    return prepare_city(graph)


def prepare_city(graph):

    """
    Add simulation properties without replacing
    the actual OpenStreetMap road geometry.
    """

    graph.graph["name"] = "NovaCity - KR Market Bengaluru"
    graph.graph["location"] = CITY_NAME
    graph.graph["map_source"] = "OpenStreetMap"

    for node, data in graph.nodes(data=True):

        data["latitude"] = data["y"]
        data["longitude"] = data["x"]

        data["signalized"] = False
        data["signal_state"] = "GREEN"

        data["pedestrian_count"] = 0
        data["pedestrian_demand"] = 0.0

        data["accident"] = False
        data["flooded"] = False

    for u, v, key, data in graph.edges(
        keys=True,
        data=True
    ):

        length = float(data.get("length", 100))

        speed = data.get("speed_kph", 30)

        if isinstance(speed, list):
            speed = speed[0]

        try:
            speed = float(speed)
        except (ValueError, TypeError):
            speed = 30.0

        lanes = data.get("lanes", 1)

        if isinstance(lanes, list):
            lanes = lanes[0]

        try:
            lanes = max(1, int(lanes))
        except (ValueError, TypeError):
            lanes = 1

        # Approximate capacity for simulation.
        capacity = lanes * 600

        data["road_id"] = f"{u}_{v}_{key}"

        data["distance"] = length
        data["length"] = length

        data["speed_limit"] = speed
        data["lanes"] = lanes

        data["capacity"] = capacity

        data["traffic"] = "Low"
        data["utilisation"] = 0.0

        data["vehicles_per_hour"] = 0.0
        data["vehicle_count"] = 0

        data["queue_length"] = 0

        data["closed"] = False
        data["accident"] = False
        data["flooded"] = False

        data["event_factor"] = 1.0
        data["flood_depth"] = 0.0

        data["travel_time"] = (
            length / max(speed, 1) * 3.6
        )

    return graph


def get_city_statistics(graph):

    return {
        "name": graph.graph.get("name"),
        "junctions": graph.number_of_nodes(),
        "road_segments": graph.number_of_edges(),
        "connected_components": (
            nx.number_weakly_connected_components(graph)
            if graph.is_directed()
            else nx.number_connected_components(graph)
        ),
        "location": graph.graph.get("location"),
        "source": graph.graph.get("map_source"),
    }


if __name__ == "__main__":

    city = load_real_city()

    print("\nNOVACITY REAL MAP STATISTICS")

    for key, value in get_city_statistics(city).items():
        print(f"{key}: {value}")