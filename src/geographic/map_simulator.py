from __future__ import annotations

import math
import random
from typing import Any

import networkx as nx
import osmnx as ox


# ============================================================
# JSON UTILITIES
# ============================================================

def clean_json(value: Any):

    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        if isinstance(value, float) and not math.isfinite(value):
            return None
        return value

    if hasattr(value, "item"):
        try:
            return clean_json(value.item())
        except Exception:
            pass

    return str(value)


def to_json(data):

    import json

    return json.dumps(
        data,
        default=clean_json,
        allow_nan=False
    )


# ============================================================
# BUILDINGS
# ============================================================

def load_buildings(center, radius_m):

    features = []

    try:

        data = ox.features_from_point(
            center,
            tags={"building": True},
            dist=int(radius_m)
        )

        for _, row in data.iterrows():

            geom = row.geometry

            if geom is None:
                continue

            if geom.geom_type not in (
                "Polygon",
                "MultiPolygon"
            ):
                continue

            if geom.geom_type == "MultiPolygon":

                geom = max(
                    geom.geoms,
                    key=lambda p: p.area
                )

            coords = [
                [float(x), float(y)]
                for x, y in geom.exterior.coords
            ]

            levels = row.get("building:levels")

            try:
                height = float(levels) * 3.2
            except (TypeError, ValueError):
                height = 10.0

            actual_height = row.get("height")

            if actual_height is not None:

                try:

                    height = float(
                        str(actual_height)
                        .replace("m", "")
                        .strip()
                    )

                except (TypeError, ValueError):
                    pass

            height = max(4, min(height, 150))

            features.append({

                "type": "Feature",

                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coords]
                },

                "properties": {
                    "height": height,
                    "name": str(row.get("name", "Building"))
                }

            })

    except Exception as error:

        print("Building download warning:", error)

    return {
        "type": "FeatureCollection",
        "features": features
    }


# ============================================================
# ROAD HELPERS
# ============================================================

def get_road_name(data):

    name = data.get("name", "Unnamed Road")

    if isinstance(name, list):
        return ", ".join(map(str, name))

    return str(name)


def get_highway_type(data):

    highway = data.get("highway", "road")

    if isinstance(highway, list):
        return str(highway[0])

    return str(highway)


def get_speed(data):

    speed = data.get("maxspeed", 30)

    if isinstance(speed, list):
        speed = speed[0]

    try:
        return float(str(speed).split()[0])
    except (ValueError, TypeError):
        return 30.0


def edge_geometry(graph, u, v, key):

    data = graph.get_edge_data(u, v, key) or {}

    geom = data.get("geometry")

    if geom is not None:

        coords = [
            [float(x), float(y)]
            for x, y in geom.coords
        ]

        # Ensure geometry follows the edge direction.
        start = graph.nodes[u]
        end = graph.nodes[v]

        first = coords[0]

        if (
            abs(first[0] - start["x"])
            + abs(first[1] - start["y"])
            >
            abs(first[0] - end["x"])
            + abs(first[1] - end["y"])
        ):
            coords.reverse()

        return coords

    return [

        [
            float(graph.nodes[u]["x"]),
            float(graph.nodes[u]["y"])
        ],

        [
            float(graph.nodes[v]["x"]),
            float(graph.nodes[v]["y"])
        ]

    ]


# ============================================================
# LOAD GEOGRAPHICAL AREA
# ============================================================

def load_area(
    place,
    radius_m=1000,
    include_buildings=False
):

    print("Searching for location:", place)

    location = ox.geocode_to_gdf(place)

    if location.empty:
        raise ValueError("Location not found: " + place)

    point = location.geometry.iloc[0].representative_point()

    center = (
        float(point.y),
        float(point.x)
    )

    print("Downloading road network...")

    graph = ox.graph_from_point(
        center_point=center,
        dist=int(radius_m),
        dist_type="bbox",
        network_type="drive",
        simplify=True,
        retain_all=False
    )

    if graph.number_of_nodes() == 0:
        raise ValueError("No road intersections found.")

    roads = []
    edge_options = []

    for u, v, key, data in graph.edges(
        keys=True,
        data=True
    ):

        coords = edge_geometry(graph, u, v, key)

        if len(coords) < 2:
            continue

        length = float(data.get("length", 1))

        if not math.isfinite(length):
            continue

        edge_id = f"{u}:{v}:{key}"

        name = get_road_name(data)

        roads.append({

            "type": "Feature",

            "geometry": {
                "type": "LineString",
                "coordinates": coords
            },

            "properties": {
                "id": edge_id,
                "name": name,
                "highway": get_highway_type(data),
                "length": length,
                "speed_kph": get_speed(data)
            }

        })

        edge_options.append({

            "id": edge_id,
            "u": u,
            "v": v,
            "key": key,
            "name": name,
            "length": length

        })

    buildings = {
        "type": "FeatureCollection",
        "features": []
    }

    if include_buildings:

        print("Downloading buildings...")

        buildings = load_buildings(
            center,
            radius_m
        )

    metadata = {

        "place": place,

        "latitude": center[0],

        "longitude": center[1],

        "radius_m": int(radius_m),

        "intersections": graph.number_of_nodes(),

        "road_segments": len(roads),

        "buildings": len(buildings["features"])

    }

    print(
        "Loaded:",
        metadata["intersections"],
        "intersections;",
        metadata["road_segments"],
        "roads."
    )

    return (
        graph,
        {
            "type": "FeatureCollection",
            "features": roads
        },
        buildings,
        edge_options,
        metadata
    )


# ============================================================
# ROUTE GEOMETRY
# ============================================================

def path_coordinates(graph, path):

    coords = []

    for u, v in zip(path[:-1], path[1:]):

        edge_data = graph.get_edge_data(u, v)

        if not edge_data:
            continue

        data = min(
            edge_data.values(),
            key=lambda item: float(item.get("length", 1))
        )

        geom = data.get("geometry")

        if geom is not None:

            part = [
                [float(x), float(y)]
                for x, y in geom.coords
            ]

            start = graph.nodes[u]

            if (
                abs(part[0][0] - start["x"])
                + abs(part[0][1] - start["y"])
                >
                abs(part[-1][0] - start["x"])
                + abs(part[-1][1] - start["y"])
            ):
                part.reverse()

        else:

            part = [
                [
                    float(graph.nodes[u]["x"]),
                    float(graph.nodes[u]["y"])
                ],
                [
                    float(graph.nodes[v]["x"]),
                    float(graph.nodes[v]["y"])
                ]
            ]

        if coords and part:

            if (
                abs(coords[-1][0] - part[0][0]) < 1e-9
                and abs(coords[-1][1] - part[0][1]) < 1e-9
            ):
                part = part[1:]

        coords.extend(part)

    return coords


# ============================================================
# SIMULATION
# ============================================================

def simulate_area(
    graph,
    roads_geojson,
    edge_options,
    event_type="None",
    affected_edge_id=None,
    vehicle_count=100,
    steps=60,
    seed=17
):

    rng = random.Random(seed)

    routing = graph.copy()

    incident = None

    affected = next(
        (
            edge for edge in edge_options
            if edge["id"] == affected_edge_id
        ),
        None
    )

    # --------------------------------------------------------
    # INCIDENT
    # --------------------------------------------------------

    if affected:

        u = affected["u"]
        v = affected["v"]
        key = affected["key"]

        coords = edge_geometry(
            graph,
            u,
            v,
            key
        )

        middle = coords[len(coords) // 2]

        incident = {

            "type": "Feature",

            "geometry": {
                "type": "Point",
                "coordinates": middle
            },

            "properties": {
                "kind": event_type
            }

        }

        if routing.has_edge(u, v):

            if event_type == "Road Closure":

                for edge_key in list(routing[u][v].keys()):

                    routing.remove_edge(
                        u,
                        v,
                        edge_key
                    )

            elif event_type in ("Accident", "Flood"):

                multiplier = (
                    2.2 if event_type == "Accident"
                    else 3.0
                )

                for data in routing[u][v].values():

                    data["length"] = (
                        float(data.get("length", 1))
                        * multiplier
                    )

    # --------------------------------------------------------
    # ROUTE GENERATION
    # --------------------------------------------------------

    nodes = list(graph.nodes)

    if len(nodes) < 2:
        raise ValueError("Insufficient intersections.")

    # A small number of unique routes are calculated and
    # reused by several vehicles to reduce computation.

    route_pool = []

    target_routes = min(
        max(15, int(vehicle_count * 0.55)),
        90
    )

    attempts = 0

    while len(route_pool) < target_routes and attempts < target_routes * 4:

        attempts += 1

        origin, destination = rng.sample(nodes, 2)

        try:

            baseline = nx.shortest_path(
                graph,
                origin,
                destination,
                weight="length"
            )

            updated = nx.shortest_path(
                routing,
                origin,
                destination,
                weight="length"
            )

            changed = baseline != updated

            route_graph = routing if changed else graph

            coords = path_coordinates(
                route_graph,
                updated
            )

            if len(coords) < 2:
                continue

            # Calculate approximate route length.
            length = 0.0

            for a, b in zip(coords[:-1], coords[1:]):

                dx = (b[0] - a[0]) * 80000
                dy = (b[1] - a[1]) * 111000

                length += math.hypot(dx, dy)

            if length < 30:
                continue

            route_pool.append({

                "coordinates": coords,

                "length": length,

                "rerouted": changed

            })

        except (
            nx.NetworkXNoPath,
            nx.NodeNotFound
        ):
            continue

    if not route_pool:
        raise ValueError(
            "Could not generate any valid vehicle routes."
        )

    # --------------------------------------------------------
    # VEHICLES
    # --------------------------------------------------------

    vehicles = []

    kinds = [
        "car",
        "car",
        "car",
        "car",
        "bus",
        "delivery",
        "emergency"
    ]

    for vehicle_id in range(int(vehicle_count)):

        route_index = vehicle_id % len(route_pool)

        route = route_pool[route_index]

        # Vehicles sharing a route are separated by their
        # initial route position.

        group_index = vehicle_id // len(route_pool)

        spacing = 0.055

        progress = (
            (group_index * spacing)
            + rng.random() * 0.008
        ) % 0.90

        kind = rng.choice(kinds)

        speed = {
            "car": rng.uniform(0.75, 1.0),
            "bus": rng.uniform(0.45, 0.65),
            "delivery": rng.uniform(0.55, 0.8),
            "emergency": rng.uniform(1.05, 1.2)
        }[kind]

        vehicles.append({

            "id": vehicle_id,

            "route": route_index,

            "progress": progress,

            "speed": speed,

            "kind": kind,

            "rerouted": route["rerouted"],

            "lane": (
                -1 if vehicle_id % 2 == 0 else 1
            )

        })

    return {

        "routes": route_pool,

        "vehicles": vehicles,

        "incident": incident,

        "vehicle_count": len(vehicles),

        "rerouted": sum(
            1 for vehicle in vehicles
            if vehicle["rerouted"]
        ),

        "event_type": event_type

    }