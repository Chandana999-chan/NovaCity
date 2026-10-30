import streamlit as st
import pandas as pd
import copy

from data.sample_data import create_sample_city, COMMUTERS

from src.events.events import (
    apply_road_closure,
    apply_accident,
    apply_flood
)

from src.events.policies import apply_bus_policy
from src.analytics.metrics import calculate_metrics
from src.visualization.city_map import create_city_map
from src.visualization.charts import create_comparison_chart


st.set_page_config(
    page_title="NovaCity Digital Twin",
    page_icon="🏙️",
    layout="wide"
)

# -----------------------------
# DASHBOARD STYLING
# -----------------------------

st.markdown("""
<style>
.stApp {
    background-color: #080f1c;
    color: white;
}
[data-testid="stMetric"] {
    background: #142238;
    padding: 18px;
    border-radius: 12px;
    border: 1px solid #263b58;
}
h1, h2, h3 {
    color: #38bdf8;
}
</style>
""", unsafe_allow_html=True)


# -----------------------------
# HEADER
# -----------------------------

st.title("🏙️ NOVACITY")
st.subheader("Fictional City Digital Twin & Simulation Platform")

st.caption(
    "Interactive urban simulation | Traffic | Public Transport | Events | Analytics"
)

st.divider()


# -----------------------------
# INITIALIZE CITY
# -----------------------------

if "city" not in st.session_state:
    st.session_state.city = create_sample_city()


# -----------------------------
# SIDEBAR CONTROLS
# -----------------------------

st.sidebar.title("Simulation Controls")

st.sidebar.subheader("Disaster & Event Management")

event_type = st.sidebar.selectbox(
    "Select an event",
    [
        "Normal Conditions",
        "Road Closure",
        "Traffic Accident",
        "Flood"
    ]
)

city = st.session_state.city
available_roads = list(city.edges())

road_labels = [
    f"{u} ↔ {v}" for u, v in available_roads
]

selected_road_label = st.sidebar.selectbox(
    "Select affected road",
    road_labels
)

selected_road = available_roads[
    road_labels.index(selected_road_label)
]


st.sidebar.subheader("Policy Interventions")

bus_frequency = st.sidebar.slider(
    "Bus frequency improvement",
    min_value=0,
    max_value=5,
    value=0,
    help="Higher values simulate reduced public transport waiting time."
)

if st.sidebar.button("Reset Simulation"):
    st.session_state.city = create_sample_city()
    st.rerun()


# -----------------------------
# BASELINE AND SCENARIO
# -----------------------------

baseline_graph = create_sample_city()
scenario_graph = copy.deepcopy(baseline_graph)


# -----------------------------
# APPLY EVENTS
# -----------------------------

if event_type == "Road Closure":
    apply_road_closure(scenario_graph, selected_road)

elif event_type == "Traffic Accident":
    apply_accident(scenario_graph, selected_road)

elif event_type == "Flood":
    apply_flood(scenario_graph, selected_road)


# -----------------------------
# APPLY POLICIES
# -----------------------------

bus_factor = apply_bus_policy(bus_frequency)


# -----------------------------
# CALCULATE METRICS
# -----------------------------

baseline = calculate_metrics(
    baseline_graph,
    COMMUTERS
)

scenario = calculate_metrics(
    scenario_graph,
    COMMUTERS,
    bus_factor
)


# -----------------------------
# KEY PERFORMANCE INDICATORS
# -----------------------------

st.markdown("### City Performance Overview")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Total Commuters",
    scenario["total_commuters"]
)

col2.metric(
    "Average Travel Time",
    f'{scenario["average_travel_time"]} min',
    delta=round(
        scenario["average_travel_time"]
        - baseline["average_travel_time"], 2
    )
)

col3.metric(
    "Affected Commuters",
    scenario["affected_commuters"]
)

col4.metric(
    "Successful Routes",
    scenario["successful_routes"]
)


st.divider()


# -----------------------------
# CITY MAP
# -----------------------------

st.markdown("### 🗺️ Live City Network")

map_col, info_col = st.columns([2, 1])

with map_col:
    st.plotly_chart(
        create_city_map(scenario_graph),
        use_container_width=True
    )

with info_col:
    st.markdown("#### Event Information")

    st.write("**Current Event:**", event_type)
    st.write("**Affected Road:**", selected_road_label)
    st.write("**Bus Improvement Level:**", bus_frequency)

    st.write(
        "**Connected Components:**",
        scenario["network_connectivity"]
    )

    st.info(
        "Red roads represent closed roads. "
        "Blue roads represent available roads."
    )


st.divider()


# -----------------------------
# ANALYTICS
# -----------------------------

st.markdown("### 📊 Simulation Analytics")

chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.plotly_chart(
        create_comparison_chart(baseline, scenario),
        use_container_width=True
    )

with chart_col2:
    comparison = pd.DataFrame({
        "Metric": [
            "Average Travel Time",
            "Affected Commuters",
            "Successful Routes"
        ],
        "Normal City": [
            baseline["average_travel_time"],
            baseline["affected_commuters"],
            baseline["successful_routes"]
        ],
        "Current Scenario": [
            scenario["average_travel_time"],
            scenario["affected_commuters"],
            scenario["successful_routes"]
        ]
    })

    st.dataframe(
        comparison,
        use_container_width=True,
        hide_index=True
    )


# -----------------------------
# COMMUTER ROUTE DETAILS
# -----------------------------

st.markdown("### 🚍 Commuter Route Analysis")

routes_df = pd.DataFrame(scenario["routes"])

st.dataframe(
    routes_df,
    use_container_width=True,
    hide_index=True
)


# -----------------------------
# SYSTEM STATUS
# -----------------------------

st.divider()

st.success(
    "NovaCity simulation executed successfully."
)

st.caption(
    "NovaCity | Smart Urban Digital Twin | Member 2 Dashboard Module"
)