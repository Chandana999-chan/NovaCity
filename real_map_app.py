import streamlit as st
import streamlit.components.v1 as components

from src.geographic.map_simulator import (
    load_area,
    simulate_area,
    to_json
)


# ============================================================
# 1. PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="NovaCity | Real-World Digital Twin",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# 2. CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    .stApp {
        background: #071321;
        color: #eaf3ff;
    }

    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 100%;
    }

    section[data-testid="stSidebar"] {
        background: #0b1929;
        border-right: 1px solid #203d58;
    }

    div[data-testid="stMetric"] {
        background: #10243a;
        border: 1px solid #254762;
        padding: 14px;
        border-radius: 12px;
    }

    div[data-testid="stMetricValue"] {
        color: #42d9c8;
    }

    div[data-testid="stMetricLabel"] {
        color: #a8bfd3;
    }

    .main-title {
        font-size: 34px;
        font-weight: 800;
        color: #eaf3ff;
    }

    .subtitle {
        color: #91abc2;
        font-size: 15px;
    }

    .status-card {
        background: #10243a;
        border: 1px solid #254762;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 12px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# 3. APPLICATION HEADER
# ============================================================

st.markdown(
    '<div class="main-title">🌍 NovaCity</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'REAL-WORLD 3D DIGITAL TWIN AND URBAN SIMULATION PLATFORM'
    '</div>',
    unsafe_allow_html=True
)

st.write("")

st.caption(
    "Explore real geographical locations, visualize road networks, "
    "simulate vehicle movement and analyze urban disruptions."
)


# ============================================================
# 4. CACHED GEOGRAPHICAL DATA
# ============================================================

@st.cache_data(
    ttl=3600,
    show_spinner=False
)
def cached_load(place, radius, include_buildings):

    return load_area(
        place=place,
        radius_m=radius,
        include_buildings=include_buildings
    )


# ============================================================
# 5. SESSION STATE
# ============================================================

default_states = {
    "geo_loaded": False,
    "geo_sim": None,
    "geo_graph": None,
    "geo_roads": None,
    "geo_buildings": None,
    "geo_edges": None,
    "geo_meta": None,
    "geo_place": None
}

for key, value in default_states.items():

    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# 6. SIDEBAR
# ============================================================

with st.sidebar:

    st.title("🌐 NovaCity Control")

    st.divider()

    st.header("📍 Geographic Location")

    place = st.text_input(
        "Search city or locality",
        value="Whitefield, Bengaluru, India",
        placeholder="Example: Indiranagar, Bengaluru, India"
    )

    radius = st.select_slider(
        "Geographical coverage",
        options=[
            500,
            750,
            1000,
            1500,
            2000,
            3000
        ],
        value=1500,
        format_func=lambda x: f"{x / 1000:g} km"
    )

    include_buildings = st.checkbox(
        "Download 3D building footprints",
        value=False,
        help=(
            "Downloads actual building footprints from "
            "OpenStreetMap. This may take additional time."
        )
    )

    load_clicked = st.button(
        "🌍 Load geographical area",
        type="primary",
        use_container_width=True
    )

    st.divider()

    st.header("🚦 Traffic Simulation")

    vehicle_count = st.slider(
        "Number of vehicles",
        min_value=20,
        max_value=300,
        value=120,
        step=10
    )

    simulation_steps = st.slider(
        "Simulation frames",
        min_value=20,
        max_value=120,
        value=60,
        step=10
    )

    event = st.selectbox(
        "Urban disruption event",
        [
            "None",
            "Accident",
            "Flood",
            "Road Closure"
        ]
    )

    st.divider()

    st.caption(
        "NovaCity | Geographic Digital Twin"
    )

    st.caption(
        "OpenStreetMap-based geographical data"
    )


# ============================================================
# 7. LOAD GEOGRAPHICAL AREA
# ============================================================

if load_clicked:

    if not place.strip():

        st.error("Please enter a geographical location.")

    else:

        try:

            with st.spinner(
                "Loading geographical data and constructing city map..."
            ):

                (
                    graph,
                    roads,
                    buildings,
                    edges,
                    meta
                ) = cached_load(
                    place.strip(),
                    int(radius),
                    include_buildings
                )

            if not roads["features"]:

                raise ValueError(
                    "No road features were returned for this location."
                )

            st.session_state.geo_graph = graph
            st.session_state.geo_roads = roads
            st.session_state.geo_buildings = buildings
            st.session_state.geo_edges = edges
            st.session_state.geo_meta = meta

            st.session_state.geo_place = place.strip()

            st.session_state.geo_loaded = True
            st.session_state.geo_sim = None

            st.success(
                f"Successfully loaded {meta['place']}."
            )

        except Exception as error:

            st.error(
                f"Unable to load geographical data: {error}"
            )

            st.info(
                "Try a more specific location, reduce the radius "
                "or check your internet connection."
            )


# ============================================================
# 8. INITIAL SCREEN
# ============================================================

if not st.session_state.geo_loaded:

    st.info(
        "Select a geographical location from the sidebar "
        "and click Load Geographical Area."
    )

    st.subheader("Platform Capabilities")

    col1, col2, col3 = st.columns(3)

    with col1:

        st.markdown(
            """
            ### 🗺️ Real Geography

            - Actual OpenStreetMap roads
            - Real intersections
            - Searchable localities
            - Geographical road geometry
            """
        )

    with col2:

        st.markdown(
            """
            ### 🏙️ 3D City Visualization

            - 3D building footprints
            - Map rotation and tilt
            - Interactive navigation
            - Building height visualization
            """
        )

    with col3:

        st.markdown(
            """
            ### 🚦 Urban Simulation

            - Synthetic vehicle movement
            - Shortest-path routing
            - Accident simulation
            - Flood and closure scenarios
            """
        )

    st.stop()


# ============================================================
# 9. RETRIEVE LOADED DATA
# ============================================================

graph = st.session_state.geo_graph

roads = st.session_state.geo_roads

buildings = st.session_state.geo_buildings

edges = st.session_state.geo_edges

meta = st.session_state.geo_meta


# ============================================================
# 10. CITY INFORMATION
# ============================================================

st.divider()

st.subheader(
    f"🏙️ {meta['place']}"
)

st.caption(
    f"Geographical center: "
    f"{meta['latitude']:.6f}, {meta['longitude']:.6f}"
)


# ============================================================
# 11. CITY METRICS
# ============================================================

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Intersections",
    f"{meta['intersections']:,}"
)

c2.metric(
    "Road Segments",
    f"{meta['road_segments']:,}"
)

c3.metric(
    "Buildings",
    f"{meta['buildings']:,}"
)

c4.metric(
    "Coverage Radius",
    f"{meta['radius_m'] / 1000:g} km"
)


# ============================================================
# 12. INCIDENT ROAD SELECTION
# ============================================================

selected_id = None

if event != "None":

    st.subheader("🚨 Incident Configuration")

    if not edges:

        st.warning(
            "No road segments are available for incident selection."
        )

    else:

        def format_edge(index):

            edge = edges[index]

            return (
                f"{edge['name']} | "
                f"{edge['length']:.1f} m | "
                f"Road ID: {edge['id']}"
            )

        selected_index = st.selectbox(
            "Choose the affected road",
            options=range(len(edges)),
            format_func=format_edge
        )

        selected_id = edges[selected_index]["id"]


# ============================================================
# 13. RUN SIMULATION
# ============================================================

st.divider()

st.subheader("🚦 Traffic Simulation")

run_simulation = st.button(
    "▶ Run Urban Simulation",
    type="primary",
    use_container_width=True
)

if run_simulation:

    try:

        with st.spinner(
            "Generating vehicle routes and calculating disruptions..."
        ):

            simulation_result = simulate_area(
                graph=graph,
                roads_geojson=roads,
                edge_options=edges,
                event_type=event,
                affected_edge_id=selected_id,
                vehicle_count=vehicle_count,
                steps=simulation_steps
            )

            st.session_state.geo_sim = simulation_result

        st.success(
            "Urban simulation completed successfully."
        )

    except Exception as error:

        st.error(
            f"Simulation failed: {error}"
        )


# ============================================================
# 14. SIMULATION RESULTS
# ============================================================

sim = st.session_state.geo_sim

if sim is None:

    sim = {
        "frames": [
            {
                "type": "FeatureCollection",
                "features": []
            }
        ],
        "incident": None,
        "vehicle_count": 0,
        "rerouted": 0,
        "event_type": "None"
    }


m1, m2, m3 = st.columns(3)

m1.metric(
    "Simulated Vehicles",
    sim["vehicle_count"]
)

m2.metric(
    "Rerouted Vehicles",
    sim["rerouted"]
)

m3.metric(
    "Current Event",
    sim["event_type"]
)


# ============================================================
# 15. MAP PAYLOAD
# ============================================================

payload = {
    "roads": roads,
    "buildings": buildings,
    "frames": sim["frames"],
    "incident": sim["incident"],

    # MapLibre expects [longitude, latitude].
    "center": [
        meta["longitude"],
        meta["latitude"]
    ],

    "place": meta["place"]
}


# ============================================================
# 16. MAPLIBRE 3D MAP
# ============================================================

html = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<link
    href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css"
    rel="stylesheet"
/>

<style>
html, body {
    margin: 0;
    padding: 0;
    width: 100%;
    height: 100%;
    overflow: hidden;
    background: #091522;
}

#map {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    background: #091522;
}

#hud {
    position: absolute;
    z-index: 5;
    top: 12px;
    left: 12px;
    max-width: 75%;
    padding: 12px 15px;
    border: 1px solid #31516d;
    border-radius: 10px;
    background: rgba(7, 19, 33, 0.95);
    color: #eaf3ff;
    font: 13px Arial, sans-serif;
    line-height: 1.6;
}

#play {
    position: absolute;
    z-index: 5;
    right: 14px;
    top: 12px;
    padding: 10px 16px;
    border: 0;
    border-radius: 8px;
    background: #087f8c;
    color: white;
    font-weight: bold;
    cursor: pointer;
}

#error {
    position: absolute;
    z-index: 10;
    bottom: 15px;
    left: 15px;
    right: 15px;
    display: none;
    padding: 12px;
    border-radius: 8px;
    background: rgba(140, 20, 30, 0.96);
    color: white;
    font: 13px Arial, sans-serif;
    overflow-wrap: anywhere;
}

.maplibregl-ctrl-group {
    background: #10243a !important;
}

.maplibregl-ctrl button {
    filter: invert(1);
}
</style>
</head>

<body>

<div id="map"></div>

<div id="hud">
    🌍 <b>NOVACITY DIGITAL TWIN</b>
    <br>
    <span id="status">Initializing geographical map...</span>
</div>

<button id="play">⏸ Pause</button>

<div id="error"></div>

<script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>

<script>

const D = __DATA__;

const statusElement = document.getElementById("status");
const errorElement = document.getElementById("error");
const playButton = document.getElementById("play");

let map = null;
let frame = 0;
let playing = true;
let timer = null;
let mapLayersAdded = false;
let fallbackAttempted = false;

function showError(message) {
    errorElement.style.display = "block";
    errorElement.textContent = "NOVACITY MAP: " + message;
    statusElement.textContent = "Map rendering problem.";
}

function hideError() {
    errorElement.style.display = "none";
}

function validateData() {

    if (!D.center || D.center.length !== 2) {
        throw new Error("Invalid map center coordinates.");
    }

    if (!D.roads || !Array.isArray(D.roads.features)) {
        throw new Error("Road GeoJSON data is missing.");
    }

    if (!D.buildings || !Array.isArray(D.buildings.features)) {
        D.buildings = {
            type: "FeatureCollection",
            features: []
        };
    }

    if (!Array.isArray(D.frames)) {
        D.frames = [];
    }

    if (!D.frames.length) {
        D.frames = [{
            type: "FeatureCollection",
            features: []
        }];
    }

    console.log("NovaCity data:", {
        center: D.center,
        roads: D.roads.features.length,
        buildings: D.buildings.features.length,
        frames: D.frames.length
    });
}


// Fallback map style using OpenStreetMap raster tiles.
// This is used if the primary OpenFreeMap style fails.

const fallbackStyle = {

    version: 8,

    sources: {

        "osm-raster": {

            type: "raster",

            tiles: [
                "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
            ],

            tileSize: 256,

            attribution:
                "© OpenStreetMap contributors"

        }

    },

    layers: [

        {

            id: "osm-background",

            type: "raster",

            source: "osm-raster"

        }

    ]

};


function addCityLayers() {

    if (mapLayersAdded) {
        return;
    }

    mapLayersAdded = true;

    try {

        // REAL ROADS

        map.addSource("osm-roads", {

            type: "geojson",

            data: D.roads

        });


        map.addLayer({

            id: "sim-roads",

            type: "line",

            source: "osm-roads",

            paint: {

                "line-color": [

                    "match",

                    ["get", "highway"],

                    "motorway", "#e5a34b",

                    "trunk", "#e5a34b",

                    "primary", "#e7c66a",

                    "secondary", "#8bb4d4",

                    "#55718a"

                ],

                "line-width": [

                    "interpolate",

                    ["linear"],

                    ["zoom"],

                    12, 1.2,

                    17, 5

                ],

                "line-opacity": 0.95

            }

        });


        // 3D BUILDINGS

        map.addSource("osm-buildings", {

            type: "geojson",

            data: D.buildings

        });


        if (D.buildings.features.length > 0) {

            map.addLayer({

                id: "sim-buildings-3d",

                type: "fill-extrusion",

                source: "osm-buildings",

                paint: {

                    "fill-extrusion-color": "#42647e",

                    "fill-extrusion-height": [

                        "get",

                        "height"

                    ],

                    "fill-extrusion-base": 0,

                    "fill-extrusion-opacity": 0.85

                }

            });

        }


        // VEHICLE SOURCE

        map.addSource("vehicles", {

            type: "geojson",

            data: D.frames[0]

        });


        map.addLayer({

            id: "vehicle-dots",

            type: "circle",

            source: "vehicles",

            paint: {

                "circle-radius": [

                    "interpolate",

                    ["linear"],

                    ["zoom"],

                    12, 3,

                    17, 6

                ],

                "circle-color": [

                    "case",

                    ["get", "rerouted"],

                    "#ffb547",

                    ["==", ["get", "kind"], "bus"],

                    "#56c9ff",

                    "#38e29a"

                ],

                "circle-stroke-color": "#071321",

                "circle-stroke-width": 1.2

            }

        });


        // INCIDENT

        if (D.incident) {

            map.addSource("incident", {

                type: "geojson",

                data: {

                    type: "FeatureCollection",

                    features: [D.incident]

                }

            });


            map.addLayer({

                id: "incident-marker",

                type: "circle",

                source: "incident",

                paint: {

                    "circle-radius": 12,

                    "circle-color": [

                        "match",

                        ["get", "kind"],

                        "Accident", "#ff4242",

                        "Flood", "#269bff",

                        "#ff9b36"

                    ],

                    "circle-stroke-color": "#ffffff",

                    "circle-stroke-width": 2

                }

            });

        }


        hideError();

        statusElement.textContent =
            D.place + " | " +
            D.roads.features.length + " road segments | " +
            D.buildings.features.length + " buildings";


        // VEHICLE ANIMATION

        if (timer) {
            clearInterval(timer);
        }

        frame = 0;

        timer = setInterval(function() {

            if (!playing || !map.getSource("vehicles")) {
                return;
            }

            frame = (frame + 1) % D.frames.length;

            map.getSource("vehicles").setData(
                D.frames[frame]
            );

            statusElement.textContent =
                "Frame " + (frame + 1) +
                " / " + D.frames.length +
                " | " +
                D.frames[frame].features.length +
                " vehicles";

        }, 180);


        console.log("NovaCity city layers loaded successfully.");

    } catch (error) {

        console.error("Layer rendering error:", error);

        showError(error.message);

    }

}


// CHECK MAPLIBRE

if (typeof maplibregl === "undefined") {

    showError(
        "MapLibre JavaScript failed to load. Check your internet connection or CDN access."
    );

} else {

    try {

        validateData();

        // INITIALIZE MAP

        map = new maplibregl.Map({

            container: "map",

            style: "https://tiles.openfreemap.org/styles/liberty",

            center: D.center,

            zoom: 15,

            pitch: 55,

            bearing: -18,

            antialias: true,

            attributionControl: true

        });


        // CONTROLS

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

        map.addControl(
            new maplibregl.ScaleControl(),
            "bottom-left"
        );


        // MAP ERRORS

        map.on("error", function(event) {

            console.error(
                "NovaCity MapLibre error:",
                event.error || event
            );

            if (!map.isStyleLoaded()) {

                statusElement.textContent =
                    "Loading map style...";

            }

        });


        // MAP STYLE LOADED

        map.on("style.load", function() {

            console.log("Map style loaded.");

        });


        // MAP READY

        map.on("load", function() {

            console.log("Base map loaded.");

            addCityLayers();

        });


        // IF THE PRIMARY MAP STYLE DOES NOT LOAD,
        // SWITCH TO THE OPENSTREETMAP RASTER FALLBACK.

        setTimeout(function() {

            if (
                map &&
                !mapLayersAdded &&
                !fallbackAttempted
            ) {

                console.warn(
                    "Primary map style did not finish loading. Trying fallback."
                );

                fallbackAttempted = true;

                statusElement.textContent =
                    "Switching to fallback map...";

                map.setStyle(fallbackStyle);

                map.once("style.load", function() {

                    console.log("Fallback map style loaded.");

                    addCityLayers();

                });

            }

        }, 15000);


        // PLAY / PAUSE

        playButton.onclick = function() {

            playing = !playing;

            this.textContent = playing
                ? "⏸ Pause"
                : "▶ Play";

        };


    } catch (error) {

        console.error("NovaCity initialization error:", error);

        showError(error.message);

    }

}

</script>

</body>
</html>
"""


# ============================================================
# 17. INJECT DATA INTO HTML
# ============================================================

html = html.replace(
    "__DATA__",
    to_json(payload)
)


# ============================================================
# 18. DISPLAY MAP
# ============================================================

components.html(
    html,
    height=760,
    scrolling=False
)

# ============================================================
# 17. INJECT DATA INTO HTML
# ============================================================

html = html.replace(
    "__DATA__",
    to_json(payload)
)


# ============================================================
# 18. DISPLAY MAP
# ============================================================

components.html(
    html,
    height=760,
    scrolling=False
)


# ============================================================
# 19. FOOTER
# ============================================================

st.divider()

st.caption(
    "NovaCity | Real-World Geographical Digital Twin"
)

st.caption(
    "Geographical data: © OpenStreetMap contributors. "
    "Vehicle movement and incident scenarios are simulated."
)


# ============================================================
# 20. SIMULATION INFORMATION
# ============================================================

with st.expander("📊 Simulation methodology and limitations"):

    st.markdown(
        """
        **Geographical data**

        The application retrieves real geographical road networks
        through OpenStreetMap and OSMnx.

        **Building visualization**

        Building footprints are downloaded from OpenStreetMap when
        enabled. Building heights use mapped values when available
        and estimated values otherwise.

        **Traffic simulation**

        Vehicles are synthetic agents moving along geographical
        road routes. They are not real vehicles or live GPS feeds.

        **Incident simulation**

        - Accident: increases the routing cost of the affected road.
        - Flood: increases the routing cost of the affected road.
        - Road closure: removes the affected directed road edge.
        - Rerouting: calculates alternative shortest paths.

        **Visualization**

        MapLibre GL JS provides interactive map navigation, rotation,
        zooming and pitch control.

        The simulation is an academic and hackathon prototype,
        not a production traffic-management system.
        """
    )