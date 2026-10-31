import json
import math
from pathlib import Path
from src.geographic.map_simulator import (
    load_area,
    simulate_area,
    to_json,
)

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from src.dashboard.integration import (
    create_sample_city,
    create_sample_commuters,
    run_dashboard_simulation,
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="NovaCity | Smart City Simulator",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CUSTOM STYLING
# ============================================================

st.markdown(
    """
    <style>
        .stApp {
            background: #071321;
            color: #e8f1ff;
        }

        section[data-testid="stSidebar"] {
            background: #0b1929;
            border-right: 1px solid #1b3852;
        }

        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 1rem;
        }

        div[data-testid="stMetric"] {
            background: #10243a;
            border: 1px solid #1d3d59;
            padding: 16px;
            border-radius: 12px;
        }

        div.stButton > button {
            background: #087f8c;
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: 600;
        }

        div.stButton > button:hover {
            background: #0aa6b5;
            color: white;
        }

        h1, h2, h3 {
            color: #e8f1ff;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SESSION STATE
# ============================================================

if "city" not in st.session_state:
    st.session_state.city = create_sample_city()

if "commuters" not in st.session_state:
    st.session_state.commuters = create_sample_commuters(
        st.session_state.city,
        num_commuters=500,
    )

if "results" not in st.session_state:
    st.session_state.results = None

if "simulation_events" not in st.session_state:
    st.session_state.simulation_events = []

if "simulation_tick" not in st.session_state:
    st.session_state.simulation_tick = 0


city = st.session_state.city
commuters = st.session_state.commuters


# ============================================================
# DATA CONVERSION HELPERS
# ============================================================

def safe_value(value):
    """Convert Python, NumPy and Pandas values into JSON-safe data."""

    if value is None:
        return None

    if isinstance(value, dict):
        return {
            str(key): safe_value(item)
            for key, item in value.items()
        }

    if isinstance(value, (tuple, list)):
        return [safe_value(item) for item in value]

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if hasattr(value, "item"):
        try:
            return safe_value(value.item())
        except (ValueError, TypeError):
            pass

    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        return int(value)

    if isinstance(value, float):
        return value if math.isfinite(value) else None

    if isinstance(value, str):
        return value

    return str(value)


def road_key(a, b):
    """Consistent identifier for an undirected road."""

    return tuple(sorted((str(a), str(b))))


def dataframe_records(dataframe):
    """Convert a DataFrame into JSON-safe dictionaries."""

    if not isinstance(dataframe, pd.DataFrame):
        return []

    if dataframe.empty:
        return []

    return [
        {
            str(key): safe_value(value)
            for key, value in record.items()
        }
        for record in dataframe.to_dict(orient="records")
    ]


def get_nested_dataframe(results, scenario, key):
    """Safely retrieve a DataFrame from baseline/disrupted results."""

    if not isinstance(results, dict):
        return pd.DataFrame()

    scenario_data = results.get(scenario, {})

    if not isinstance(scenario_data, dict):
        return pd.DataFrame()

    dataframe = scenario_data.get(key)

    if isinstance(dataframe, pd.DataFrame):
        return dataframe

    return pd.DataFrame()


def get_summary_value(key, default=0):
    """Get a summary value safely."""

    value = summary.get(key, default)

    if value is None:
        return default

    return value


# ============================================================
# EXTRACT ACTUAL ENGINE RESULTS
# ============================================================

def extract_simulation_data(results):

    baseline_routes = get_nested_dataframe(
        results, "baseline", "final_routes"
    )

    disrupted_routes = get_nested_dataframe(
        results, "disrupted", "final_routes"
    )

    baseline_traffic = get_nested_dataframe(
        results, "baseline", "traffic"
    )

    disrupted_traffic = get_nested_dataframe(
        results, "disrupted", "traffic"
    )

    comparison = results.get("comparison", pd.DataFrame())

    if not isinstance(comparison, pd.DataFrame):
        comparison = pd.DataFrame()

    disrupted_data = results.get("disrupted", {})

    if not isinstance(disrupted_data, dict):
        disrupted_data = {}

    return {
        "baseline_routes": baseline_routes,
        "disrupted_routes": disrupted_routes,
        "baseline_traffic": baseline_traffic,
        "disrupted_traffic": disrupted_traffic,
        "comparison": comparison,
        "vehicle_history": disrupted_data.get(
            "vehicle_history", []
        ),
        "vehicles": disrupted_data.get("vehicles", []),
        "pedestrians": disrupted_data.get("pedestrians", []),
        "signals": disrupted_data.get("signals", []),
        "affected_roads": disrupted_data.get("affected_roads", []),
    }


# ============================================================
# CITY PAYLOAD FOR THREE.JS
# ============================================================

def get_city_payload(graph, traffic_df=None, events=None):

    import networkx as nx

    # --------------------------------------------------------
    # INITIALIZATION
    # --------------------------------------------------------

    nodes = []
    roads = []
    node_positions = {}

    traffic_lookup = {}
    event_lookup = {}

    # --------------------------------------------------------
    # TRAFFIC DATA LOOKUP
    # --------------------------------------------------------

    if isinstance(traffic_df, pd.DataFrame):

        for _, row in traffic_df.iterrows():

            start = row.get("start", row.get("u"))
            end = row.get("end", row.get("v"))

            if start is None or end is None:
                continue

            traffic_lookup[road_key(start, end)] = {
                "vehicles": safe_value(row.get("vehicles", 0)),

                "vehicles_per_hour": safe_value(
                    row.get("vehicles_per_hour", 0)
                ),

                "utilisation": safe_value(
                    row.get("utilisation", 0)
                ),

                "queue_length": safe_value(
                    row.get("queue_length", 0)
                ),

                "travel_time": safe_value(
                    row.get("travel_time", 0)
                ),

                "traffic_level": safe_value(
                    row.get("traffic_level", "low")
                ),

                "closed": bool(row.get("closed", False)),
                "accident": bool(row.get("accident", False)),
                "flooded": bool(row.get("flooded", False)),
            }

    # --------------------------------------------------------
    # EVENT LOOKUP
    # --------------------------------------------------------

    for event in events or []:

        road = event.get("road")

        if isinstance(road, (tuple, list)) and len(road) == 2:

            event_lookup[road_key(road[0], road[1])] = (
                event.get("type")
            )

    # --------------------------------------------------------
    # NODES
    # --------------------------------------------------------

    for node, attributes in graph.nodes(data=True):

        x = safe_value(attributes.get("x", 0))
        z = safe_value(attributes.get("y", 0))

        node_positions[node] = (x, z)

        nodes.append({
            "id": str(node),
            "x": x,
            "z": z,

            "district": str(
                attributes.get("district", "Central District")
            ),

            "type": str(
                attributes.get(
                    "node_type",
                    attributes.get("type", "junction")
                )
            ),
        })

    # --------------------------------------------------------
    # ROADS
    # --------------------------------------------------------

    for source, destination, attributes in graph.edges(data=True):

        if (
            source not in node_positions
            or destination not in node_positions
        ):
            continue

        x1, z1 = node_positions[source]
        x2, z2 = node_positions[destination]

        key = road_key(source, destination)

        traffic_data = traffic_lookup.get(key, {})

        event_type = event_lookup.get(key, "none")

        closed = bool(
            attributes.get("closed", False)
            or traffic_data.get("closed", False)
        )

        accident = bool(
            attributes.get("accident", False)
            or traffic_data.get("accident", False)
        )

        flooded = bool(
            attributes.get("flooded", False)
            or traffic_data.get("flooded", False)
        )

        roads.append({

            "source": str(source),
            "target": str(destination),

            "x1": x1,
            "z1": z1,

            "x2": x2,
            "z2": z2,

            "distance": safe_value(
                attributes.get("distance", 1)
            ),

            "capacity": safe_value(
                attributes.get("capacity", 100)
            ),

            "speed": safe_value(
                attributes.get("speed", 40)
            ),

            "traffic": traffic_data.get(
                "vehicles_per_hour",
                safe_value(attributes.get("traffic", 0))
            ),

            "vehicles": traffic_data.get("vehicles", 0),

            "utilisation": traffic_data.get(
                "utilisation", 0
            ),

            "queue_length": traffic_data.get(
                "queue_length", 0
            ),

            "travel_time": traffic_data.get(
                "travel_time", 0
            ),

            "traffic_level": traffic_data.get(
                "traffic_level", "low"
            ),

            "closed": closed,
            "accident": accident,
            "flooded": flooded,

            "event_type": event_type,
        })

    # --------------------------------------------------------
    # DIAGNOSTICS
    # --------------------------------------------------------

    if graph.is_directed():
        connected = nx.is_weakly_connected(graph)
    else:
        connected = nx.is_connected(graph)

    print("\n========== NOVACITY GRAPH ==========")
    print("CITY GRAPH CONNECTED:", connected)
    print("TOTAL JUNCTIONS:", len(nodes))
    print("TOTAL ROADS:", len(roads))

    for road in roads:
        print(
            road["source"], "->", road["target"],
            "| Start:", road["x1"], road["z1"],
            "| End:", road["x2"], road["z2"],
            "| Closed:", road["closed"],
            "| Accident:", road["accident"]
        )

    print("====================================\n")

    return {
        "nodes": nodes,
        "roads": roads,
    }

# ============================================================
# NAVIGATION
# ============================================================

st.sidebar.markdown("# 🏙️ NovaCity")
st.sidebar.caption("Fictional City Simulation Platform")

st.sidebar.divider()

application_mode = st.sidebar.radio(
    "APPLICATION MODE",
    [
        "Fictional City Simulator",
        "Real Geographic Digital Twin",
    ],
)

st.sidebar.divider()

# ============================================================
# REAL GEOGRAPHIC DIGITAL TWIN
# ============================================================

if application_mode == "Real Geographic Digital Twin":

    st.title("🌍 NovaCity — Real Geographic Digital Twin")

    st.caption(
        "Real OpenStreetMap road networks with animated "
        "synthetic urban traffic."
    )

    # --------------------------------------------------------
    # CACHED GEOGRAPHICAL DOWNLOAD
    # --------------------------------------------------------

    @st.cache_data(
        ttl=3600,
        show_spinner=False
    )
    def get_geographic_area(place, radius, buildings):

        return load_area(
            place,
            radius,
            buildings
        )

    # --------------------------------------------------------
    # SESSION STATE
    # --------------------------------------------------------

    defaults = {
        "real_graph": None,
        "real_roads": None,
        "real_buildings": None,
        "real_edges": None,
        "real_meta": None,
        "real_simulation": None,
        "real_loaded_place": None,
    }

    for key, value in defaults.items():

        if key not in st.session_state:
            st.session_state[key] = value

    # --------------------------------------------------------
    # LOCATION CONTROLS
    # --------------------------------------------------------

    with st.sidebar:

        st.subheader("📍 Geographic Location")

        location = st.text_input(
            "Search locality",
            value="Whitefield, Bengaluru, India",
            key="real_location"
        )

        radius = st.select_slider(
            "Coverage radius",
            options=[
                500,
                750,
                1000,
                1500,
                2000
            ],
            value=1000,
            format_func=lambda x: f"{x} metres"
        )

        download_buildings = st.checkbox(
            "Download 3D building footprints",
            value=False
        )

        load_button = st.button(
            "🌍 Load City",
            type="primary",
            use_container_width=True
        )

        st.divider()

        st.subheader("🚗 Traffic")

        vehicle_count = st.slider(
            "Vehicle population",
            20,
            150,
            80,
            10
        )

        event = st.selectbox(
            "Urban incident",
            [
                "None",
                "Accident",
                "Flood",
                "Road Closure"
            ]
        )

    # --------------------------------------------------------
    # LOAD CITY
    # --------------------------------------------------------

    if load_button:

        if not location.strip():

            st.error("Enter a location.")

        else:

            try:

                with st.spinner(
                    "Downloading geographical road data..."
                ):

                    (
                        graph,
                        roads,
                        buildings,
                        edges,
                        meta
                    ) = get_geographic_area(
                        location.strip(),
                        radius,
                        download_buildings
                    )

                st.session_state.real_graph = graph

                st.session_state.real_roads = roads

                st.session_state.real_buildings = buildings

                st.session_state.real_edges = edges

                st.session_state.real_meta = meta

                st.session_state.real_loaded_place = location.strip()

                st.session_state.real_simulation = None

                st.success("Geographical city loaded.")

            except Exception as error:

                st.error(f"Geographical loading failed: {error}")

    # --------------------------------------------------------
    # CHECK LOADED CITY
    # --------------------------------------------------------

    if st.session_state.real_graph is None:

        st.info(
            "Enter a locality and click Load City to begin."
        )

        st.stop()

    graph = st.session_state.real_graph

    roads = st.session_state.real_roads

    buildings = st.session_state.real_buildings

    edges = st.session_state.real_edges

    meta = st.session_state.real_meta

    # --------------------------------------------------------
    # CITY METRICS
    # --------------------------------------------------------

    st.subheader(meta["place"])

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Intersections",
        f"{meta['intersections']:,}"
    )

    c2.metric(
        "Road segments",
        f"{meta['road_segments']:,}"
    )

    c3.metric(
        "Buildings",
        f"{meta['buildings']:,}"
    )

    c4.metric(
        "Coverage",
        f"{meta['radius_m']} m"
    )

    st.divider()

    # --------------------------------------------------------
    # INCIDENT ROAD
    # --------------------------------------------------------

    selected_edge_id = None

    if event != "None" and edges:

        selected_edge = st.selectbox(
            "Select affected road",
            options=edges,
            format_func=lambda e: (
                f"{e['name']} — {e['length']:.0f} m"
            ),
            key="real_affected_road"
        )

        selected_edge_id = selected_edge["id"]

    # --------------------------------------------------------
    # SIMULATION
    # --------------------------------------------------------

    run = st.button(
        "▶ Generate Traffic Simulation",
        type="primary",
        use_container_width=True
    )

    if run:

        try:

            with st.spinner(
                "Calculating routes and generating traffic..."
            ):

                st.session_state.real_simulation = simulate_area(
                    graph=graph,
                    roads_geojson=roads,
                    edge_options=edges,
                    event_type=event,
                    affected_edge_id=selected_edge_id,
                    vehicle_count=vehicle_count,
                    seed=17
                )

        except Exception as error:

            st.error(f"Simulation error: {error}")

    sim = st.session_state.real_simulation

    # --------------------------------------------------------
    # DEFAULT EMPTY SIMULATION
    # --------------------------------------------------------

    if sim is None:

        sim = {
            "routes": [],
            "vehicles": [],
            "incident": None,
            "vehicle_count": 0,
            "rerouted": 0,
            "event_type": "None"
        }

        st.info(
            "Click Generate Traffic Simulation to animate vehicles."
        )

    # --------------------------------------------------------
    # SIMULATION METRICS
    # --------------------------------------------------------

    a, b, c = st.columns(3)

    a.metric(
        "Vehicles",
        sim["vehicle_count"]
    )

    b.metric(
        "Rerouted",
        sim["rerouted"]
    )

    c.metric(
        "Incident",
        sim["event_type"]
    )

    # --------------------------------------------------------
    # MAP DATA
    # --------------------------------------------------------

    payload = {

        "center": [
            meta["longitude"],
            meta["latitude"]
        ],

        "place": meta["place"],

        "roads": roads,

        "buildings": buildings,

        "routes": sim["routes"],

        "vehicles": sim["vehicles"],

        "incident": sim["incident"],

    }

    # --------------------------------------------------------
    # MAP HTML
    # --------------------------------------------------------

    html = r"""
<!DOCTYPE html>
<html>
<head>

<meta charset="utf-8">

<meta name="viewport"
content="width=device-width, initial-scale=1">

<link
href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css"
rel="stylesheet"
/>

<style>

html, body, #map {
    margin: 0;
    width: 100%;
    height: 100%;
    overflow: hidden;
    background: #091522;
}

#map {
    position: absolute;
    inset: 0;
}

#hud {
    position: absolute;
    z-index: 5;
    top: 12px;
    left: 12px;
    padding: 12px;
    border-radius: 10px;
    color: white;
    background: rgba(7,19,33,.94);
    font: 13px Arial;
}

#status {
    color: #61d9ce;
}

#play {
    position: absolute;
    z-index: 5;
    top: 12px;
    right: 12px;
    padding: 10px 16px;
    border: none;
    border-radius: 8px;
    background: #087f8c;
    color: white;
    cursor: pointer;
}

</style>

</head>

<body>

<div id="map"></div>

<div id="hud">
    🌍 NOVACITY DIGITAL TWIN
    <br>
    <span id="status">Loading map...</span>
</div>

<button id="play">⏸ Pause</button>

<script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>

<script>

const D = __DATA__;

const status = document.getElementById("status");

const playButton = document.getElementById("play");

let playing = true;

let lastTime = 0;

let elapsed = 0;

let vehicles = [];

let map;

function interpolate(route, progress) {

    const coords = route.coordinates;

    if (!coords || coords.length < 2) {
        return null;
    }

    let lengths = [];

    let total = 0;

    for (let i = 0; i < coords.length - 1; i++) {

        const a = coords[i];

        const b = coords[i + 1];

        const dx = (b[0] - a[0]) * 80000;

        const dy = (b[1] - a[1]) * 111000;

        const distance = Math.hypot(dx, dy);

        lengths.push(distance);

        total += distance;

    }

    if (total <= 0) {
        return null;
    }

    let target = progress * total;

    let walked = 0;

    for (let i = 0; i < lengths.length; i++) {

        const distance = lengths[i];

        if (walked + distance >= target) {

            const ratio = (
                target - walked
            ) / Math.max(distance, 0.001);

            const a = coords[i];

            const b = coords[i + 1];

            return [
                a[0] + (b[0] - a[0]) * ratio,
                a[1] + (b[1] - a[1]) * ratio
            ];

        }

        walked += distance;

    }

    return coords[coords.length - 1];

}


// Offset vehicles slightly to simulate separate lanes.

function laneOffset(point, route, lane) {

    const coords = route.coordinates;

    const index = Math.min(
        1,
        coords.length - 1
    );

    const a = coords[index - 1];

    const b = coords[index];

    const dx = (b[0] - a[0]) * 80000;

    const dy = (b[1] - a[1]) * 111000;

    const length = Math.max(
        Math.hypot(dx, dy),
        0.001
    );

    const offset = lane * 2.2;

    const perpendicularX = -dy / length;

    const perpendicularY = dx / length;

    return [
        point[0] + perpendicularX * offset / 80000,
        point[1] + perpendicularY * offset / 111000
    ];

}


// Prevent overlapping visible vehicles in screen space.

function separateVehicles(features) {

    const accepted = [];

    const occupied = [];

    for (const feature of features) {

        const pixel = map.project(
            feature.geometry.coordinates
        );

        let clear = true;

        for (const other of occupied) {

            const distance = Math.hypot(
                pixel.x - other.x,
                pixel.y - other.y
            );

            if (distance < 11) {

                clear = false;

                break;

            }

        }

        if (clear) {

            accepted.push(feature);

            occupied.push(pixel);

        }

    }

    return accepted;

}


function initialize() {

    map = new maplibregl.Map({

        container: "map",

        style: "https://tiles.openfreemap.org/styles/liberty",

        center: D.center,

        zoom: 15,

        pitch: 58,

        bearing: -15,

        antialias: true

    });

    map.addControl(
        new maplibregl.NavigationControl({
            visualizePitch: true
        }),
        "top-right"
    );

    map.addControl(
        new maplibregl.FullscreenControl(),
        "top-right"
    );

    map.on("load", function() {

        map.addSource("roads", {
            type: "geojson",
            data: D.roads
        });

        map.addLayer({

            id: "roads-layer",

            type: "line",

            source: "roads",

            paint: {

                "line-color": [

                    "match",

                    ["get", "highway"],

                    "motorway", "#f4a34e",

                    "primary", "#e9c66c",

                    "secondary", "#91b7d5",

                    "#647e94"

                ],

                "line-width": [

                    "interpolate",

                    ["linear"],

                    ["zoom"],

                    12, 1,

                    17, 4

                ]

            }

        });


        if (D.buildings.features.length > 0) {

            map.addSource("buildings", {

                type: "geojson",

                data: D.buildings

            });

            map.addLayer({

                id: "buildings-3d",

                type: "fill-extrusion",

                source: "buildings",

                paint: {

                    "fill-extrusion-color": "#456985",

                    "fill-extrusion-height": [
                        "get",
                        "height"
                    ],

                    "fill-extrusion-opacity": 0.82

                }

            });

        }


        map.addSource("vehicles", {

            type: "geojson",

            data: {
                type: "FeatureCollection",
                features: []
            }

        });


        map.addLayer({

            id: "vehicles-layer",

            type: "circle",

            source: "vehicles",

            paint: {

                "circle-radius": [

                    "match",

                    ["get", "kind"],

                    "bus", 5,

                    "emergency", 5,

                    3.5

                ],

                "circle-color": [

                    "match",

                    ["get", "kind"],

                    "bus", "#38bdf8",

                    "delivery", "#fbbf24",

                    "emergency", "#f43f5e",

                    "#38e29a"

                ],

                "circle-stroke-color": "#071321",

                "circle-stroke-width": 1.2

            }

        });


        if (D.incident) {

            map.addSource("incident", {

                type: "geojson",

                data: {

                    type: "FeatureCollection",

                    features: [D.incident]

                }

            });

            map.addLayer({

                id: "incident-layer",

                type: "circle",

                source: "incident",

                paint: {

                    "circle-radius": 11,

                    "circle-color": "#ff4242",

                    "circle-stroke-color": "#ffffff",

                    "circle-stroke-width": 2

                }

            });

        }


        vehicles = D.vehicles.map(v => ({

            ...v,

            progress: v.progress,

            speed: v.speed

        }));


        status.textContent =
            D.place + " | " +
            D.roads.features.length + " roads | " +
            vehicles.length + " vehicles";


        requestAnimationFrame(animate);

    });

}


function animate(timestamp) {

    requestAnimationFrame(animate);

    if (!playing) {
        lastTime = timestamp;
        return;
    }

    if (!lastTime) {
        lastTime = timestamp;
        return;
    }

    const delta = Math.min(
        (timestamp - lastTime) / 1000,
        0.05
    );

    lastTime = timestamp;

    elapsed += delta;

    const features = [];

    for (const vehicle of vehicles) {

        const route = D.routes[vehicle.route];

        if (!route) continue;

        const length = Math.max(
            route.length,
            50
        );

        // Approximate movement in metres per second.
        const metresPerSecond =
            vehicle.speed * 7.5;

        vehicle.progress += (
            metresPerSecond * delta / length
        );

        if (vehicle.progress >= 1) {
            vehicle.progress = 0;
        }

        let point = interpolate(
            route,
            vehicle.progress
        );

        if (!point) continue;

        point = laneOffset(
            point,
            route,
            vehicle.lane
        );

        features.push({

            type: "Feature",

            geometry: {

                type: "Point",

                coordinates: point

            },

            properties: {

                id: vehicle.id,

                kind: vehicle.kind,

                rerouted: vehicle.rerouted

            }

        });

    }

    const separated = separateVehicles(features);

    map.getSource("vehicles").setData({

        type: "FeatureCollection",

        features: separated

    });

    if (Math.floor(elapsed) % 2 === 0) {

        status.textContent =
            D.place + " | " +
            separated.length + " visible vehicles | LIVE SIMULATION";

    }

}


playButton.onclick = function() {

    playing = !playing;

    this.textContent = playing
        ? "⏸ Pause"
        : "▶ Play";

};


initialize();

</script>

</body>
</html>
"""

    # --------------------------------------------------------
    # INJECT DATA
    # --------------------------------------------------------

    html = html.replace(
        "__DATA__",
        to_json(payload)
    )

    # --------------------------------------------------------
    # DISPLAY MAP
    # --------------------------------------------------------

    components.html(
        html,
        height=760,
        scrolling=False
    )

    st.caption(
        "OpenStreetMap geographical data. "
        "Vehicle movements and incidents are simulated."
    )

    st.stop()
st.sidebar.divider()

pages = [
    "City Overview",
    "3D City Explorer",
    "Road & Traffic",
    "Pedestrian Mobility",
    "Traffic Signals",
    "Flood & Environment",
    "Infrastructure",
    "Analytics",
]

page = st.sidebar.radio(
    "NAVIGATION",
    pages,
)

st.sidebar.divider()


# ============================================================
# SIMULATION CONTROLS
# ============================================================

st.sidebar.markdown("### ⚙️ Simulation Controls")

vehicle_density = st.sidebar.slider(
    "Vehicle Density",
    min_value=0,
    max_value=100,
    value=58,
    help="Controls the visual vehicle population.",
)

pedestrian_activity = st.sidebar.slider(
    "Pedestrian Activity",
    min_value=0,
    max_value=100,
    value=45,
    help="Controls the visual pedestrian population.",
)

bus_frequency = st.sidebar.slider(
    "Bus Frequency",
    min_value=0,
    max_value=12,
    value=5,
    help="Controls the visual bus population.",
)

st.sidebar.divider()


# ============================================================
# EVENT CONTROLS
# ============================================================

st.sidebar.markdown("### 🚨 City Events")

event_type = st.sidebar.selectbox(
    "Select Event",
    [
        "None",
        "Road Closure",
        "Accident",
        "Flood",
    ],
)

available_roads = list(city.edges())

road_labels = [
    f"{source} ↔ {destination}"
    for source, destination in available_roads
]

selected_road_index = st.sidebar.selectbox(
    "Affected Road",
    range(len(available_roads)),
    format_func=lambda index: road_labels[index],
)

selected_road = available_roads[selected_road_index]


if st.sidebar.button(
    "➕ Add Event",
    use_container_width=True,
):

    if event_type != "None":

        event_mapping = {
            "Road Closure": "road_closure",
            "Accident": "accident",
            "Flood": "flood",
        }

        new_event = {
            "type": event_mapping[event_type],
            "road": tuple(selected_road),
        }

        if new_event not in st.session_state.simulation_events:

            st.session_state.simulation_events.append(
                new_event
            )

        st.sidebar.success(
            f"{event_type} added. Run the simulation to apply it."
        )


if st.sidebar.button(
    "🗑️ Clear All Events",
    use_container_width=True,
):

    st.session_state.simulation_events = []

    st.sidebar.success(
        "Events cleared. Run the simulation to reset the city."
    )


if st.session_state.simulation_events:

    st.sidebar.markdown("**Active Events**")

    for index, event in enumerate(
        st.session_state.simulation_events,
        start=1,
    ):

        st.sidebar.write(
            f"{index}. "
            f"{event['type'].replace('_', ' ').title()} — "
            f"{event['road'][0]} ↔ {event['road'][1]}"
        )


# ============================================================
# RUN SIMULATION
# ============================================================

st.sidebar.divider()

run_clicked = st.sidebar.button(
    "▶ RUN CITY SIMULATION",
    use_container_width=True,
    type="primary",
)


if run_clicked:

    with st.spinner(
        "Running NovaCity simulation and calculating commuter routes..."
    ):

        st.session_state.results = run_dashboard_simulation(
            city,
            commuters,
            events=st.session_state.simulation_events,
        )

        st.session_state.simulation_tick += 1

    st.sidebar.success("Simulation completed!")


# Baseline simulation on first launch

if st.session_state.results is None:

    with st.spinner("Initializing baseline city simulation..."):

        st.session_state.results = run_dashboard_simulation(
            city,
            commuters,
            events=[],
        )


results = st.session_state.results

summary = results.get("summary", {})

simulation_data = extract_simulation_data(results)


# ============================================================
# USE THE DISRUPTED GRAPH FOR VISUALIZATION
# ============================================================

disrupted_data = results.get("disrupted", {})

if isinstance(disrupted_data, dict):

    visualization_graph = disrupted_data.get("graph", city)

else:

    visualization_graph = city


# ============================================================
# PREPARE THREE.JS DATA
# ============================================================

city_payload = get_city_payload(
    visualization_graph,
    traffic_df=simulation_data["disrupted_traffic"],
    events=st.session_state.simulation_events,
)


visualization_data = {

    "page": page,

    "city": city_payload,

    "summary": {
        key: safe_value(value)
        for key, value in summary.items()
    },

    "vehicle_density": vehicle_density,

    "pedestrian_activity": pedestrian_activity,

    "bus_frequency": bus_frequency,

    "events": [
        {
            "type": event["type"],
            "road": [
                str(event["road"][0]),
                str(event["road"][1]),
            ],
        }
        for event in st.session_state.simulation_events
    ],

    # Actual engine route records
    "routes": dataframe_records(
        simulation_data["disrupted_routes"]
    ),

    "baseline_routes": dataframe_records(
        simulation_data["baseline_routes"]
    ),

    # Actual engine traffic records
    "traffic": dataframe_records(
        simulation_data["disrupted_traffic"]
    ),

    "baseline_traffic": dataframe_records(
        simulation_data["baseline_traffic"]
    ),

    "comparison": dataframe_records(
        simulation_data["comparison"]
    ),

    # Additional simulation outputs
    "vehicle_history": safe_value(
        simulation_data["vehicle_history"]
    ),

    "vehicles": safe_value(
        simulation_data["vehicles"]
    ),

    "pedestrians": safe_value(
        simulation_data["pedestrians"]
    ),

    "signals": safe_value(
        simulation_data["signals"]
    ),

    "affected_roads": safe_value(
        simulation_data["affected_roads"]
    ),

    "tick": st.session_state.simulation_tick,

    "results_available": True,
}


# ============================================================
# ANALYTICS PAGE
# ============================================================

def show_analytics():

    st.title("📊 NovaCity Analytics")

    st.caption(
        "Actual metrics generated by the NovaCity Python simulation engine."
    )

    # --------------------------------------------------------
    # COMMUTER METRICS
    # --------------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Total Commuters",
        get_summary_value("total_commuters"),
    )

    col2.metric(
        "Reachable",
        get_summary_value("reachable_commuters"),
    )

    col3.metric(
        "Delayed",
        get_summary_value("delayed_commuters"),
    )

    col4.metric(
        "Unreachable",
        get_summary_value("unreachable_commuters"),
    )

    st.divider()

    # --------------------------------------------------------
    # TRAVEL TIME METRICS
    # --------------------------------------------------------

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Baseline Travel Time",
        f"{get_summary_value('baseline_average_time'):.2f} min",
    )

    col2.metric(
        "Disrupted Travel Time",
        f"{get_summary_value('disrupted_average_time'):.2f} min",
    )

    col3.metric(
        "Average Extra Time",
        f"{get_summary_value('average_extra_time'):.2f} min",
    )

    st.divider()

    # --------------------------------------------------------
    # NETWORK METRICS
    # --------------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Changed Routes",
        get_summary_value("changed_routes"),
    )

    col2.metric(
        "Affected Roads",
        get_summary_value("affected_road_segments"),
    )

    col3.metric(
        "Average Road Utilisation",
        f"{get_summary_value('average_road_utilisation'):.3f}",
    )

    col4.metric(
        "Congested Roads",
        get_summary_value("congested_road_segments"),
    )

    st.divider()

    # --------------------------------------------------------
    # TRAFFIC ANALYSIS
    # --------------------------------------------------------

    st.subheader("🚦 Road Traffic Analysis")

    traffic_df = simulation_data["disrupted_traffic"]

    if not traffic_df.empty:

        display_columns = [
            column
            for column in [
                "start",
                "end",
                "road_name",
                "vehicles",
                "vehicles_per_hour",
                "capacity",
                "utilisation",
                "queue_length",
                "travel_time",
                "traffic_level",
                "closed",
                "accident",
                "flooded",
            ]
            if column in traffic_df.columns
        ]

        st.dataframe(
            traffic_df[display_columns],
            use_container_width=True,
            hide_index=True,
        )

        if "utilisation" in traffic_df.columns:

            chart_df = traffic_df.copy()

            if "start" in chart_df.columns and "end" in chart_df.columns:

                chart_df["road_name"] = (
                    chart_df["start"].astype(str)
                    + " ↔ "
                    + chart_df["end"].astype(str)
                )

                st.subheader("Road Utilisation")

                st.bar_chart(
                    chart_df.set_index("road_name")["utilisation"]
                )

    else:

        st.info("No traffic records are available.")

    st.divider()

    # --------------------------------------------------------
    # ROUTE COMPARISON
    # --------------------------------------------------------

    st.subheader("🧭 Commuter Route Comparison")

    comparison_df = simulation_data["comparison"]

    if not comparison_df.empty:

        st.dataframe(
            comparison_df,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info("No route comparison data is available.")

    st.divider()

    # --------------------------------------------------------
    # FINAL ROUTES
    # --------------------------------------------------------

    st.subheader("🚗 Disrupted Commuter Routes")

    routes_df = simulation_data["disrupted_routes"]

    if not routes_df.empty:

        st.dataframe(
            routes_df,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info("No commuter route records are available.")


# ============================================================
# MAIN APPLICATION
# ============================================================

if page == "Analytics":

    show_analytics()

else:

    page_titles = {

        "City Overview": "🏙️ NovaCity — City Overview",

        "3D City Explorer": "🌐 3D City Explorer",

        "Road & Traffic": "🚗 Road & Traffic Simulation",

        "Pedestrian Mobility": "🚶 Pedestrian Mobility",

        "Traffic Signals": "🚦 Traffic Signal Network",

        "Flood & Environment": "🌊 Flood & Environment",

        "Infrastructure": "🏥 City Infrastructure",

    }

    st.title(
        page_titles.get(page, "NovaCity")
    )

    st.caption(
        "Interactive 3D city environment powered by Three.js "
        "and the NovaCity Python simulation engine."
    )

    # --------------------------------------------------------
    # QUICK METRICS
    # --------------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Commuters",
        get_summary_value("total_commuters"),
    )

    col2.metric(
        "Reachable",
        get_summary_value("reachable_commuters"),
    )

    col3.metric(
        "Delayed",
        get_summary_value("delayed_commuters"),
    )

    col4.metric(
        "Active Events",
        len(st.session_state.simulation_events),
    )

    st.divider()

    # --------------------------------------------------------
    # THREE.JS VISUALIZATION
    # --------------------------------------------------------

    html_path = Path(__file__).parent / "city_view.html"

    if not html_path.exists():

        st.error(
            "city_view.html was not found in the NovaCity root folder."
        )

        st.code(str(html_path))

    else:

        html_content = html_path.read_text(
            encoding="utf-8"
        )

        data_json = json.dumps(
            visualization_data,
            allow_nan=False,
            ensure_ascii=False,
        )

        html_content = html_content.replace(
            "__NOVACITY_DATA__",
            data_json,
        )

        components.html(
            html_content,
            height=780,
            scrolling=False,
        )


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
    <div style="
        text-align:center;
        color:#7891aa;
        padding:16px;
        font-size:12px;
    ">
        NOVACITY • Fictional City Simulator • Interactive Urban Simulation
    </div>
    """,
    unsafe_allow_html=True,
)