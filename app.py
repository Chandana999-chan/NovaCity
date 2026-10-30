import json
import math
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import folium

from src.city.city import load_real_city
from src.simulation.commuters import generate_commuters
from src.dashboard.integration import run_dashboard_simulation
from src.events.events import create_event


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="NovaCity | Bengaluru Simulator",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

CENTER_LAT = 12.9645
CENTER_LON = 77.5761889

st.markdown("""
<style>
    .stApp {
        background: #0b1120;
        color: #e5e7eb;
    }

    [data-testid="stSidebar"] {
        background: #111827;
        border-right: 1px solid #263449;
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }

    .main-title {
        font-size: 2.3rem;
        font-weight: 800;
        color: #f8fafc;
        margin-bottom: 0;
    }

    .subtitle {
        color: #94a3b8;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }

    .metric-card {
        background: #111c2e;
        border: 1px solid #263449;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 10px;
    }

    .metric-label {
        color: #94a3b8;
        font-size: 0.85rem;
    }

    .metric-value {
        color: #f8fafc;
        font-size: 1.7rem;
        font-weight: 700;
    }

    .section-heading {
        color: #e2e8f0;
        font-size: 1.2rem;
        font-weight: 700;
        margin-top: 1rem;
        margin-bottom: 0.8rem;
    }

    div[data-testid="stButton"] button {
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# SESSION STATE
# ============================================================

def initialise_session_state():

    defaults = {
        "city": None,
        "commuters": None,
        "results": None,
        "simulation_events": [],
        "map_features": None,
        "simulation_tick": 0
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


initialise_session_state()


# ============================================================
# LOAD CITY AND COMMUTERS
# ============================================================

@st.cache_resource(show_spinner="Loading Bengaluru road network...")
def get_city():
    return load_real_city()


def load_project_data():

    if st.session_state.city is None:
        st.session_state.city = get_city()

    if st.session_state.commuters is None:
        with st.spinner("Generating commuter demand..."):
            st.session_state.commuters = generate_commuters(
                st.session_state.city,
                num_commuters=500
            )


# ============================================================
# GENERAL HELPERS
# ============================================================

def safe_value(value, default=0):

    try:
        if pd.isna(value):
            return default
        return value
    except (TypeError, ValueError):
        return default


def format_number(value, digits=2):

    try:
        return f"{float(value):,.{digits}f}"
    except (TypeError, ValueError):
        return "0"


def get_edge_name(data):

    name = data.get("name", "Unnamed Road")

    if isinstance(name, list):
        return ", ".join(str(item) for item in name)

    return str(name)


def get_edge_coordinates(graph, u, v, key):

    data = graph.edges[u, v, key]

    geometry = data.get("geometry")

    if geometry is not None:

        try:
            if geometry.geom_type == "LineString":
                coordinates = list(geometry.coords)

            elif geometry.geom_type == "MultiLineString":
                coordinates = []

                for line in geometry.geoms:
                    line_coords = list(line.coords)

                    if coordinates and line_coords:
                        if coordinates[-1] == line_coords[0]:
                            coordinates.extend(line_coords[1:])
                        else:
                            coordinates.extend(line_coords)
                    else:
                        coordinates.extend(line_coords)

            else:
                coordinates = []

            if len(coordinates) >= 2:
                # Shapely coordinates are longitude, latitude.
                return [
                    [float(lat), float(lon)]
                    for lon, lat in coordinates
                ]

        except Exception:
            pass

    # Fallback: use the endpoint coordinates.
    node_u = graph.nodes[u]
    node_v = graph.nodes[v]

    return [
        [float(node_u["y"]), float(node_u["x"])],
        [float(node_v["y"]), float(node_v["x"])]
    ]


def simplify_coordinates(coordinates, max_points=20):

    if len(coordinates) <= max_points:
        return coordinates

    step = max(1, math.ceil(len(coordinates) / max_points))

    simplified = coordinates[::step]

    if simplified[-1] != coordinates[-1]:
        simplified.append(coordinates[-1])

    return simplified


# ============================================================
# MAP DATA PREPARATION
# ============================================================

def build_map_features(graph):

    """
    Converts the MultiDiGraph into a compact GeoJSON FeatureCollection.

    Parallel and reverse-direction edges with identical geometry
    are represented by one physical road feature.
    """

    grouped = {}

    for u, v, key, data in graph.edges(keys=True, data=True):

        try:
            coordinates = get_edge_coordinates(graph, u, v, key)

            if len(coordinates) < 2:
                continue

            coordinates = simplify_coordinates(
                coordinates,
                max_points=20
            )

            # Canonical geometry signature handles reverse duplicates.
            forward = tuple(
                (round(lat, 6), round(lon, 6))
                for lat, lon in coordinates
            )

            backward = tuple(reversed(forward))

            signature = min(forward, backward)

            if signature not in grouped:

                grouped[signature] = {
                    "coordinates": coordinates,
                    "edge_ids": [],
                    "name": get_edge_name(data),
                    "length": safe_value(data.get("length"), 0),
                    "lanes": safe_value(data.get("lanes"), 1)
                }

            grouped[signature]["edge_ids"].append(
                [str(u), str(v), str(key)]
            )

        except Exception:
            continue

    features = []

    for item in grouped.values():

        # GeoJSON requires longitude, latitude.
        geojson_coordinates = [
            [lon, lat]
            for lat, lon in item["coordinates"]
        ]

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": geojson_coordinates
            },
            "properties": {
                "name": item["name"],
                "length": item["length"],
                "lanes": str(item["lanes"]),
                "edge_ids": item["edge_ids"]
            }
        })

    return {
        "type": "FeatureCollection",
        "features": features
    }


def get_map_road_data():

    if st.session_state.map_features is None:

        with st.spinner("Preparing Bengaluru road map..."):

            st.session_state.map_features = build_map_features(
                st.session_state.city
            )

    return st.session_state.map_features


# ============================================================
# TRAFFIC DATA
# ============================================================

def get_traffic_lookup():

    results = st.session_state.results

    if not results:
        return {}

    traffic = results.get("final_traffic")

    if traffic is None or traffic.empty:
        return {}

    lookup = {}

    for _, row in traffic.iterrows():

        try:
            key = (
                str(row["start"]),
                str(row["end"]),
                str(row["key"])
            )

            lookup[key] = {
                "utilisation": safe_value(
                    row.get("utilisation"), 0
                ),
                "vehicles_per_hour": safe_value(
                    row.get("vehicles_per_hour"), 0
                ),
                "travel_time": safe_value(
                    row.get("travel_time"), 0
                )
            }

        except (KeyError, TypeError):
            continue

    return lookup


def get_edge_traffic(edge_ids, traffic_lookup):

    values = []

    for edge_id in edge_ids:

        key = tuple(edge_id)

        if key in traffic_lookup:
            values.append(traffic_lookup[key])

    if not values:
        return {
            "utilisation": 0,
            "vehicles_per_hour": 0,
            "travel_time": 0
        }

    return {
        "utilisation": max(
            item["utilisation"] for item in values
        ),
        "vehicles_per_hour": sum(
            item["vehicles_per_hour"] for item in values
        ),
        "travel_time": max(
            item["travel_time"] for item in values
        )
    }


def get_traffic_color(utilisation):

    try:
        utilisation = float(utilisation)
    except (TypeError, ValueError):
        utilisation = 0

    if utilisation >= 1.0:
        return "#ef4444"

    if utilisation >= 0.75:
        return "#f97316"

    if utilisation >= 0.45:
        return "#eab308"

    return "#22c55e"


# ============================================================
# EVENT HELPERS
# ============================================================

def get_event_edge_ids(event):

    road = event.get("road")

    if isinstance(road, (list, tuple)):

        if len(road) == 3:
            return [str(road[0]), str(road[1]), str(road[2])]

        if len(road) == 2:
            return [str(road[0]), str(road[1])]

    return None


def get_event_coordinates(graph, event):

    road = event.get("road")

    if not isinstance(road, (list, tuple)):
        return None

    if len(road) == 3:
        u, v, key = road

    elif len(road) == 2:
        u, v = road
        key = None

    else:
        return None

    try:

        if key is not None:
            coordinates = get_edge_coordinates(graph, u, v, key)

        else:
            edge_data = graph.get_edge_data(u, v)

            if not edge_data:
                return None

            first_key = next(iter(edge_data))
            coordinates = get_edge_coordinates(
                graph, u, v, first_key
            )

        middle = coordinates[len(coordinates) // 2]

        return middle

    except Exception:
        return None


def event_color(event_type):

    colors = {
        "accident": "#ef4444",
        "flood": "#3b82f6",
        "road_closure": "#a855f7"
    }

    return colors.get(event_type, "#facc15")


# ============================================================
# MAP CONSTRUCTION
# ============================================================

def create_city_map():

    graph = st.session_state.city

    road_features = get_map_road_data()
    traffic_lookup = get_traffic_lookup()

    city_map = folium.Map(
        location=[CENTER_LAT, CENTER_LON],
        zoom_start=16,
        tiles="OpenStreetMap",
        control_scale=True,
        prefer_canvas=True
    )

    # Build traffic-aware GeoJSON features.
    display_features = []

    for feature in road_features["features"]:

        properties = feature["properties"]

        traffic = get_edge_traffic(
            properties["edge_ids"],
            traffic_lookup
        )

        properties["utilisation"] = traffic["utilisation"]
        properties["vehicles_per_hour"] = traffic["vehicles_per_hour"]

        display_features.append(feature)

    display_geojson = {
        "type": "FeatureCollection",
        "features": display_features
    }

    def road_style(feature):

        utilisation = feature["properties"].get(
            "utilisation", 0
        )

        return {
            "color": get_traffic_color(utilisation),
            "weight": 3,
            "opacity": 0.85
        }

    folium.GeoJson(
        display_geojson,
        name="Bengaluru Roads",
        style_function=road_style,
        tooltip=folium.GeoJsonTooltip(
            fields=["name", "utilisation", "vehicles_per_hour"],
            aliases=[
                "Road:",
                "Utilisation:",
                "Vehicles/hour:"
            ],
            localize=True
        )
    ).add_to(city_map)

    # K.R. Market marker.
    folium.Marker(
        location=[CENTER_LAT, CENTER_LON],
        tooltip="K.R. Market",
        popup="NovaCity simulation centre",
        icon=folium.Icon(
            color="blue",
            icon="building",
            prefix="fa"
        )
    ).add_to(city_map)

    # Event markers.
    for event in st.session_state.simulation_events:

        coordinates = get_event_coordinates(graph, event)

        if coordinates is None:
            continue

        event_type = event.get("type", "event")
        severity = event.get("severity", "moderate")

        folium.CircleMarker(
            location=coordinates,
            radius=9,
            color=event_color(event_type),
            fill=True,
            fill_color=event_color(event_type),
            fill_opacity=0.9,
            tooltip=f"{event_type.title()} | {severity.title()}"
        ).add_to(city_map)

    folium.LayerControl().add_to(city_map)

    return city_map


def display_city_map():

    city_map = create_city_map()

    # Render Folium directly as HTML.
    # This avoids streamlit-folium's repeated bidirectional map state.
    map_html = city_map.get_root().render()

    components.html(
        map_html,
        height=700,
        scrolling=False
    )


# ============================================================
# SIMULATION
# ============================================================

def run_current_simulation(simulation_hours, iterations):

    with st.spinner("Running NovaCity simulation..."):

        results = run_dashboard_simulation(
            city=st.session_state.city,
            commuters=st.session_state.commuters,
            events=st.session_state.simulation_events,
            simulation_hours=simulation_hours,
            iterations=iterations
        )

        st.session_state.results = results
        st.session_state.simulation_tick += 1


def get_summary():

    if not st.session_state.results:
        return {}

    return st.session_state.results.get("summary", {})


# ============================================================
# METRIC DISPLAY
# ============================================================

def metric_card(label, value, suffix=""):

    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}{suffix}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def display_overview_metrics():

    summary = get_summary()

    if not summary:
        st.info("Run the simulation to view city metrics.")
        return

    columns = st.columns(4)

    with columns[0]:
        metric_card(
            "Total Commuters",
            format_number(summary.get("total_commuters", 0), 0)
        )

    with columns[1]:
        metric_card(
            "Average Commute",
            format_number(summary.get("average_commute_time", 0)),
            " min"
        )

    with columns[2]:
        metric_card(
            "Affected Commuters",
            format_number(summary.get("affected_commuters", 0), 0)
        )

    with columns[3]:
        metric_card(
            "Changed Routes",
            format_number(summary.get("changed_routes", 0), 0)
        )


# ============================================================
# SIDEBAR
# ============================================================

def render_sidebar():

    st.sidebar.markdown("# 🏙️ NovaCity")
    st.sidebar.caption("Bengaluru Urban Simulation")

    pages = [
        "City Overview",
        "Road & Traffic",
        "Pedestrian Mobility",
        "Traffic Signals",
        "Flood & Environment",
        "Infrastructure",
        "Analytics"
    ]

    selected_page = st.sidebar.radio(
        "Navigation",
        pages
    )

    st.sidebar.divider()

    st.sidebar.markdown("### Simulation Controls")

    commuter_count = st.sidebar.slider(
        "Commuter demand",
        min_value=100,
        max_value=1000,
        value=500,
        step=100
    )

    simulation_hours = st.sidebar.slider(
        "Simulation duration (hours)",
        min_value=1,
        max_value=12,
        value=3
    )

    iterations = st.sidebar.slider(
        "Traffic assignment iterations",
        min_value=1,
        max_value=5,
        value=3
    )

    if st.sidebar.button(
        "Apply commuter demand",
        use_container_width=True
    ):

        with st.spinner("Generating commuter demand..."):

            st.session_state.commuters = generate_commuters(
                st.session_state.city,
                num_commuters=commuter_count
            )

            st.session_state.results = None

        st.sidebar.success(
            f"{commuter_count} commuters generated."
        )

    if st.sidebar.button(
        "▶ Run Simulation",
        use_container_width=True,
        type="primary"
    ):

        run_current_simulation(
            simulation_hours,
            iterations
        )

        st.sidebar.success("Simulation completed.")

    st.sidebar.divider()

    st.sidebar.markdown("### Simulation Events")

    graph = st.session_state.city

    edge_options = list(graph.edges(keys=True))

    if edge_options:

        edge_labels = {}

        for u, v, key in edge_options:

            data = graph.edges[u, v, key]

            road_name = get_edge_name(data)

            label = (
                f"{road_name} | "
                f"{str(u)[:8]} → {str(v)[:8]} | "
                f"{str(key)}"
            )

            edge_labels[label] = (u, v, key)

        selected_label = st.sidebar.selectbox(
            "Select road segment",
            list(edge_labels.keys())
        )

        selected_road = edge_labels[selected_label]

        event_type = st.sidebar.selectbox(
            "Event type",
            [
                "accident",
                "flood",
                "road_closure"
            ]
        )

        severity = st.sidebar.selectbox(
            "Severity",
            [
                "low",
                "moderate",
                "high",
                "critical"
            ]
        )

        flood_depth = st.sidebar.slider(
            "Flood depth (metres)",
            min_value=0.0,
            max_value=1.0,
            value=0.3,
            step=0.05
        )

        if st.sidebar.button(
            "＋ Add Event",
            use_container_width=True
        ):

            event = create_event(
                event_type=event_type,
                road=selected_road,
                severity=severity,
                flood_depth=flood_depth
            )

            st.session_state.simulation_events.append(event)
            st.session_state.results = None

            st.sidebar.success(
                f"{event_type.title()} added."
            )

    st.sidebar.write(
        f"Active events: {len(st.session_state.simulation_events)}"
    )

    if st.sidebar.button(
        "Clear All Events",
        use_container_width=True
    ):

        st.session_state.simulation_events = []
        st.session_state.results = None

        st.sidebar.success("All events cleared.")

    return selected_page


# ============================================================
# CITY OVERVIEW
# ============================================================

def render_city_overview():

    st.markdown(
        '<div class="main-title">NovaCity</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">'
        'Real-road digital city simulation | K.R. Market, Bengaluru'
        '</div>',
        unsafe_allow_html=True
    )

    graph = st.session_state.city

    columns = st.columns(4)

    with columns[0]:
        metric_card(
            "Road Network Nodes",
            format_number(graph.number_of_nodes(), 0)
        )

    with columns[1]:
        metric_card(
            "Directed Road Segments",
            format_number(graph.number_of_edges(), 0)
        )

    with columns[2]:
        metric_card(
            "Commuters",
            format_number(len(st.session_state.commuters), 0)
        )

    with columns[3]:
        metric_card(
            "Active Events",
            format_number(len(st.session_state.simulation_events), 0)
        )

    st.markdown(
        '<div class="section-heading">Bengaluru Road Network</div>',
        unsafe_allow_html=True
    )

    st.caption(
        "Road geometry is sourced from OpenStreetMap. "
        "Traffic demand and disruption effects are simulated, "
        "not live traffic measurements."
    )

    display_city_map()

    st.markdown(
        '<div class="section-heading">Simulation Summary</div>',
        unsafe_allow_html=True
    )

    display_overview_metrics()


# ============================================================
# ROAD AND TRAFFIC
# ============================================================

def render_road_traffic():

    st.title("🚦 Road & Traffic")

    st.caption(
        "Road network and simulated traffic congestion."
    )

    display_city_map()

    results = st.session_state.results

    if not results:
        st.info("Run the simulation to generate traffic results.")
        return

    traffic = results.get("final_traffic")

    if traffic is None or traffic.empty:
        st.warning("No traffic results are available.")
        return

    columns = st.columns(3)

    with columns[0]:
        metric_card(
            "Road Segments Analysed",
            format_number(len(traffic), 0)
        )

    with columns[1]:
        metric_card(
            "Average Utilisation",
            format_number(
                traffic["utilisation"].mean() * 100
                if "utilisation" in traffic else 0
            ),
            "%"
        )

    with columns[2]:
        metric_card(
            "Total Simulated Flow",
            format_number(
                traffic["vehicles_per_hour"].sum()
                if "vehicles_per_hour" in traffic else 0
            ),
            " veh/hr"
        )

    st.subheader("Highest Traffic Road Segments")

    if "utilisation" in traffic.columns:

        top_roads = traffic.sort_values(
            "utilisation",
            ascending=False
        ).head(20)

        display_columns = [
            column for column in [
                "road_id",
                "road",
                "vehicles_per_hour",
                "capacity",
                "utilisation",
                "travel_time",
                "closed",
                "flooded",
                "accident"
            ]
            if column in top_roads.columns
        ]

        st.dataframe(
            top_roads[display_columns],
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# PEDESTRIAN MOBILITY
# ============================================================

def render_pedestrian_mobility():

    st.title("🚶 Pedestrian Mobility")

    st.write(
        "This section represents pedestrian activity around "
        "K.R. Market. Pedestrian density is currently a simulation "
        "input and is not measured from live pedestrian sensors."
    )

    pedestrian_activity = st.slider(
        "Pedestrian activity level",
        min_value=0,
        max_value=100,
        value=65
    )

    estimated_density = pedestrian_activity * 12

    columns = st.columns(2)

    with columns[0]:
        metric_card(
            "Activity Level",
            pedestrian_activity,
            "%"
        )

    with columns[1]:
        metric_card(
            "Illustrative Density",
            estimated_density,
            " people/km²"
        )

    display_city_map()


# ============================================================
# TRAFFIC SIGNALS
# ============================================================

def render_traffic_signals():

    st.title("🚥 Traffic Signals")

    st.write(
        "Traffic signal control is a planned simulation component. "
        "The current road network provides road geometry and "
        "connectivity; signal timing is not supplied by OSM."
    )

    signal_cycle = st.slider(
        "Illustrative signal cycle (seconds)",
        min_value=30,
        max_value=180,
        value=90
    )

    green_time = st.slider(
        "Green phase (seconds)",
        min_value=10,
        max_value=120,
        value=45
    )

    red_time = max(signal_cycle - green_time, 0)

    columns = st.columns(3)

    with columns[0]:
        metric_card("Cycle Duration", signal_cycle, " sec")

    with columns[1]:
        metric_card("Green Phase", green_time, " sec")

    with columns[2]:
        metric_card("Remaining Phase", red_time, " sec")

    st.info(
        "These are configurable signal parameters for the "
        "planned signal simulation, not live signal-controller data."
    )

    display_city_map()


# ============================================================
# FLOOD AND ENVIRONMENT
# ============================================================

def render_flood_environment():

    st.title("🌧️ Flood & Environment")

    st.write(
        "Simulate flood events on selected road segments. "
        "Flood depth changes road capacity and can close severely "
        "affected roads."
    )

    flood_events = [
        event for event in st.session_state.simulation_events
        if event.get("type") == "flood"
    ]

    columns = st.columns(2)

    with columns[0]:
        metric_card(
            "Active Flood Events",
            len(flood_events)
        )

    with columns[1]:
        metric_card(
            "Total Active Events",
            len(st.session_state.simulation_events)
        )

    if flood_events:

        st.subheader("Flood Event Details")

        flood_table = []

        for event in flood_events:

            flood_table.append({
                "Event ID": event.get("event_id", ""),
                "Severity": event.get("severity", ""),
                "Flood Depth (m)": event.get("flood_depth", 0),
                "Duration (min)": event.get("duration_minutes", 0)
            })

        st.dataframe(
            pd.DataFrame(flood_table),
            use_container_width=True,
            hide_index=True
        )

    display_city_map()


# ============================================================
# INFRASTRUCTURE
# ============================================================

def render_infrastructure():

    st.title("🏥 City Infrastructure")

    graph = st.session_state.city

    road_count = graph.number_of_edges()
    node_count = graph.number_of_nodes()

    columns = st.columns(3)

    with columns[0]:
        metric_card("Road Segments", road_count)

    with columns[1]:
        metric_card("Network Intersections / Nodes", node_count)

    with columns[2]:
        metric_card(
            "Commuters Generated",
            len(st.session_state.commuters)
        )

    st.info(
        "The current implementation focuses on the road network "
        "and mobility simulation. Hospitals, schools, utilities, "
        "and other facility-level service models can be integrated "
        "as separate infrastructure layers."
    )

    display_city_map()


# ============================================================
# ANALYTICS
# ============================================================

def render_analytics():

    st.title("📊 Simulation Analytics")

    results = st.session_state.results

    if not results:
        st.info(
            "Run the simulation to view analytics and performance."
        )
        return

    summary = results.get("summary", {})

    columns = st.columns(4)

    with columns[0]:
        metric_card(
            "Total Commuters",
            summary.get("total_commuters", 0)
        )

    with columns[1]:
        metric_card(
            "Reachable",
            summary.get("reachable_commuters", 0)
        )

    with columns[2]:
        metric_card(
            "Unreachable",
            summary.get("unreachable_commuters", 0)
        )

    with columns[3]:
        metric_card(
            "Affected",
            summary.get("affected_commuters", 0)
        )

    st.subheader("Travel Time Comparison")

    baseline_time = summary.get(
        "baseline_average_commute_time", 0
    )

    disrupted_time = summary.get(
        "average_commute_time", 0
    )

    comparison = pd.DataFrame({
        "Scenario": ["Baseline", "With Events"],
        "Average Travel Time (minutes)": [
            baseline_time,
            disrupted_time
        ]
    })

    st.bar_chart(
        comparison.set_index("Scenario")
    )

    st.subheader("Impact Summary")

    impact_columns = st.columns(3)

    with impact_columns[0]:
        metric_card(
            "Baseline Average",
            format_number(baseline_time),
            " min"
        )

    with impact_columns[1]:
        metric_card(
            "Disrupted Average",
            format_number(disrupted_time),
            " min"
        )

    with impact_columns[2]:
        metric_card(
            "Average Extra Time",
            format_number(
                summary.get("average_extra_time", 0)
            ),
            " min"
        )

    st.subheader("Network Impact")

    network_data = {
        "Metric": [
            "Changed Routes",
            "Affected Road Segments",
            "Events Applied",
            "Average Road Utilisation"
        ],
        "Value": [
            summary.get("changed_routes", 0),
            summary.get("affected_road_segments", 0),
            summary.get("events_applied", 0),
            summary.get("average_road_utilisation", 0)
        ]
    }

    st.dataframe(
        pd.DataFrame(network_data),
        use_container_width=True,
        hide_index=True
    )

    st.subheader("Commuter Route Results")

    routes = results.get("final_routes")

    if routes is not None and not routes.empty:

        display_columns = [
            column for column in [
                "commuter_id",
                "origin",
                "destination",
                "transport_mode",
                "distance",
                "travel_time"
            ]
            if column in routes.columns
        ]

        st.dataframe(
            routes[display_columns],
            use_container_width=True,
            hide_index=True
        )

    st.subheader("Traffic Results")

    traffic = results.get("final_traffic")

    if traffic is not None and not traffic.empty:

        st.dataframe(
            traffic.head(100),
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# MAIN APPLICATION
# ============================================================

def main():

    load_project_data()

    selected_page = render_sidebar()

    if selected_page == "City Overview":
        render_city_overview()

    elif selected_page == "Road & Traffic":
        render_road_traffic()

    elif selected_page == "Pedestrian Mobility":
        render_pedestrian_mobility()

    elif selected_page == "Traffic Signals":
        render_traffic_signals()

    elif selected_page == "Flood & Environment":
        render_flood_environment()

    elif selected_page == "Infrastructure":
        render_infrastructure()

    elif selected_page == "Analytics":
        render_analytics()

    st.markdown("---")

    st.caption(
        "NovaCity | Bengaluru Road Network Simulation | "
        "OpenStreetMap geography + simulated mobility and disruptions"
    )


if __name__ == "__main__":
    main()