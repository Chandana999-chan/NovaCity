import json
import math
from pathlib import Path

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

    nodes = []
    roads = []

    traffic_lookup = {}

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

    event_lookup = {}

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

        nodes.append(
            {
                "id": str(node),
                "x": safe_value(attributes.get("x", 0)),
                "z": safe_value(attributes.get("y", 0)),
                "district": str(
                    attributes.get("district", "Central District")
                ),
                "type": str(
                    attributes.get("type", "junction")
                ),
            }
        )

    # --------------------------------------------------------
    # ROADS
    # --------------------------------------------------------

    for source, destination, attributes in graph.edges(data=True):

        source_data = graph.nodes[source]
        destination_data = graph.nodes[destination]

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

        roads.append(
            {
                "source": str(source),
                "target": str(destination),

                "x1": safe_value(
                    source_data.get("x", 0)
                ),

                "z1": safe_value(
                    source_data.get("y", 0)
                ),

                "x2": safe_value(
                    destination_data.get("x", 0)
                ),

                "z2": safe_value(
                    destination_data.get("y", 0)
                ),

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
                    safe_value(attributes.get("traffic", 0)),
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
            }
        )

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