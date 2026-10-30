import streamlit as st
import pandas as pd
import plotly.express as px

from streamlit_autorefresh import st_autorefresh

from src.visualization.city_scene import (
    create_city,
    generate_vehicles,
    generate_pedestrians,
    update_signals,
    render_city
)

st.set_page_config(
    page_title="NovaCity | 3D Digital Twin",
    page_icon="🏙️",
    layout="wide"
)

# --------------------------------------------------
# GLASSMORPHISM THEME
# --------------------------------------------------

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

* {
    font-family: Inter, sans-serif;
}

.stApp {
    background:
      radial-gradient(ellipse at 50% 0%, #143c59 0%, transparent 50%),
      linear-gradient(135deg,#030914,#081827,#071322);
    color: white;
}

.block-container {
    max-width: 1900px;
    padding-top: 1rem;
}

[data-testid="stSidebar"] {
    background: rgba(4,15,29,.97);
    border-right: 1px solid rgba(50,200,255,.25);
}

[data-testid="stMetric"] {
    background: linear-gradient(140deg,
        rgba(25,80,115,.65),
        rgba(8,24,42,.85));
    border: 1px solid rgba(65,205,255,.22);
    padding: 15px;
    border-radius: 15px;
    box-shadow: 0 8px 30px rgba(0,0,0,.25);
}

[data-testid="stMetricValue"] {
    color: #5ce7ff;
    font-weight: 800;
}

.glass {
    background: linear-gradient(
        145deg,
        rgba(35,90,125,.35),
        rgba(7,22,40,.80)
    );
    border: 1px solid rgba(80,210,255,.23);
    border-radius: 18px;
    padding: 18px;
    box-shadow: 0 12px 35px rgba(0,0,0,.3);
    backdrop-filter: blur(18px);
}

.neon {
    color: #42dfff;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 2px;
}

.muted {
    color: #8daec4;
    font-size: 12px;
}

h1 {
    font-size: 30px !important;
    font-weight: 800 !important;
}

h2,h3 {
    color: #e6f8ff !important;
}

hr {
    border-color: rgba(70,190,230,.18);
}

.stButton button {
    background: linear-gradient(100deg,#086486,#087eaa);
    color: white;
    border: 1px solid #32c9f5;
    border-radius: 9px;
    font-weight: 700;
}

</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "city" not in st.session_state:
    st.session_state.city = create_city()

if "tick" not in st.session_state:
    st.session_state.tick = 0

if "running" not in st.session_state:
    st.session_state.running = False

if "closed_roads" not in st.session_state:
    st.session_state.closed_roads = []


city = st.session_state.city


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:

    st.markdown("# 🏙 NOVACITY")

    st.markdown(
        '<div class="neon">URBAN DIGITAL TWIN</div>',
        unsafe_allow_html=True
    )

    st.success("● CITY SYSTEM ONLINE")

    page = st.radio(
        "CITY MODULES",
        [
            "Overview",
            "3D City Explorer",
            "Traffic Simulation",
            "Pedestrian Simulation",
            "Traffic Signals",
            "Infrastructure",
            "Analytics"
        ]
    )

    st.divider()

    st.markdown("### SIMULATION CONTROLS")

    density = st.slider(
        "Vehicle Density",
        0, 100, 55
    )

    pedestrian_count = st.slider(
        "Pedestrian Population",
        0, 100, 35
    )

    bus_frequency = st.slider(
        "Bus Frequency",
        0, 10, 5
    )

    signal_duration = st.slider(
        "Signal Duration",
        2, 30, 10
    )

    speed = st.slider(
        "Simulation Speed",
        1, 10, 3
    )

    pitch = st.slider(
        "3D Camera Tilt",
        0, 85, 65
    )

    bearing = st.slider(
        "360° Camera Rotation",
        0, 359, 0
    )

    zoom = st.slider(
        "Camera Zoom",
        12.0, 18.0, 14.5
    )

    st.divider()

    if st.button("▶ START SIMULATION", use_container_width=True):
        st.session_state.running = True

    if st.button("⏸ PAUSE SIMULATION", use_container_width=True):
        st.session_state.running = False

    if st.button("↻ RESET CITY", use_container_width=True):
        st.session_state.tick = 0
        st.session_state.city = create_city()
        st.session_state.closed_roads = []
        st.rerun()


# --------------------------------------------------
# SIMULATION CLOCK
# --------------------------------------------------

if st.session_state.running:

    st_autorefresh(
        interval=max(100, 1000 // speed),
        key="city_refresh"
    )

    st.session_state.tick += 1


tick = st.session_state.tick


# --------------------------------------------------
# GENERATE MOVING ENTITIES
# --------------------------------------------------

vehicles = generate_vehicles(
    city,
    tick,
    density,
    bus_frequency
)

pedestrians = generate_pedestrians(
    city,
    tick,
    pedestrian_count
)

signals = update_signals(
    city,
    tick,
    signal_duration
)


# --------------------------------------------------
# APPLY ROAD CLOSURES
# --------------------------------------------------

for road in city["roads"]:

    if road["name"] in st.session_state.closed_roads:
        road["width"] = 15


# --------------------------------------------------
# COMMON FUNCTIONS
# --------------------------------------------------

def header(title, subtitle):

    st.markdown(f"# {title}")

    st.markdown(
        f'<div class="muted">{subtitle}</div>',
        unsafe_allow_html=True
    )

    st.divider()


def show_map(height=700):

    deck = render_city(
        city,
        vehicles,
        pedestrians,
        signals,
        bearing=bearing,
        pitch=pitch,
        zoom=zoom
    )

    st.pydeck_chart(
        deck,
        height=height,
        width="stretch"
    )


# --------------------------------------------------
# OVERVIEW
# --------------------------------------------------

if page == "Overview":

    header(
        "NOVACITY COMMAND CENTER",
        "Interactive urban digital twin and intelligent city simulation"
    )

    a,b,c,d,e = st.columns(5)

    a.metric("Population", "126,500")
    b.metric("Buildings", len(city["buildings"]))
    c.metric("Vehicles", len(vehicles))
    d.metric("Pedestrians", len(pedestrians))
    e.metric("Traffic Signals", len(signals))

    left, right = st.columns([3.5, 1])

    with left:

        st.markdown(
            '<div class="glass"><div class="neon">LIVE 3D CITY ENVIRONMENT</div></div>',
            unsafe_allow_html=True
        )

        show_map(720)

    with right:

        st.markdown("### CITY STATUS")

        st.markdown(
            """
            <div class="glass">
                <h3 style="color:#39e8ae">OPERATIONAL</h3>
                <p>🟢 Road network</p>
                <p>🟢 Building infrastructure</p>
                <p>🟢 Vehicle simulation</p>
                <p>🟢 Pedestrian simulation</p>
                <p>🟢 Traffic signals</p>
                <p>🟢 Public facilities</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("### SIMULATION")

        st.metric("Simulation Tick", tick)

        st.metric(
            "Simulation Status",
            "RUNNING" if st.session_state.running else "PAUSED"
        )

    st.markdown("## City Composition")

    buildings = pd.DataFrame(city["buildings"])

    fig = px.pie(
        buildings,
        names="type",
        hole=.55,
        template="plotly_dark",
        title="Building Distribution"
    )

    st.plotly_chart(fig, use_container_width=True)


# --------------------------------------------------
# 3D CITY EXPLORER
# --------------------------------------------------

elif page == "3D City Explorer":

    header(
        "360° CITY EXPLORER",
        "Rotate, tilt and explore the entire fictional city"
    )

    st.info(
        "Drag the 3D map to rotate. Use the mouse wheel to zoom. "
        "Use the camera controls in the sidebar for precise positioning."
    )

    show_map(800)

    buildings = pd.DataFrame(city["buildings"])

    st.markdown("## Building Inventory")

    st.dataframe(
        buildings[["name", "type", "floors", "height"]],
        width="stretch",
        hide_index=True
    )


# --------------------------------------------------
# TRAFFIC SIMULATION
# --------------------------------------------------

elif page == "Traffic Simulation":

    header(
        "INTELLIGENT TRAFFIC CONTROL",
        "Simulated cars, buses and emergency vehicle movement"
    )

    a,b,c = st.columns(3)

    a.metric("Total Vehicles", len(vehicles))

    a_bus = sum(v["type"] == "Bus" for v in vehicles)
    a_emergency = sum(v["type"] == "Emergency" for v in vehicles)

    b.metric("Buses", a_bus)
    c.metric("Emergency Vehicles", a_emergency)

    show_map(720)

    st.markdown("## Road Incident Controls")

    road_names = [r["name"] for r in city["roads"]]

    selected = st.selectbox(
        "Select a road",
        road_names
    )

    col1,col2 = st.columns(2)

    with col1:

        if st.button("🚧 Close Selected Road"):

            if selected not in st.session_state.closed_roads:
                st.session_state.closed_roads.append(selected)

            st.rerun()

    with col2:

        if st.button("🟢 Reopen Selected Road"):

            if selected in st.session_state.closed_roads:
                st.session_state.closed_roads.remove(selected)

            st.rerun()

    st.write("Closed roads:", st.session_state.closed_roads)


# --------------------------------------------------
# PEDESTRIAN SIMULATION
# --------------------------------------------------

elif page == "Pedestrian Simulation":

    header(
        "PEDESTRIAN MOVEMENT SYSTEM",
        "Pedestrian movement across city sidewalks and urban routes"
    )

    a,b = st.columns(2)

    a.metric("Active Pedestrians", len(pedestrians))
    b.metric("Simulation Tick", tick)

    show_map(720)

    st.info(
        "Pedestrians currently follow simulated walking paths. "
        "Signal-aware crossing and collision avoidance are future "
        "integration tasks for the simulation engine."
    )


# --------------------------------------------------
# TRAFFIC SIGNALS
# --------------------------------------------------

elif page == "Traffic Signals":

    header(
        "SMART TRAFFIC SIGNAL NETWORK",
        "Traffic light states and intersection management"
    )

    a,b,c = st.columns(3)

    a.metric(
        "Green Signals",
        sum(s["state"] == "GREEN" for s in signals)
    )

    b.metric(
        "Yellow Signals",
        sum(s["state"] == "YELLOW" for s in signals)
    )

    c.metric(
        "Red Signals",
        sum(s["state"] == "RED" for s in signals)
    )

    show_map(720)

    st.markdown("## Signal Registry")

    st.dataframe(
        pd.DataFrame(signals)[["name", "state"]],
        width="stretch",
        hide_index=True
    )


# --------------------------------------------------
# INFRASTRUCTURE
# --------------------------------------------------

elif page == "Infrastructure":

    header(
        "CITY INFRASTRUCTURE",
        "Building, hospital, school, transport and emergency services"
    )

    show_map(720)

    buildings = pd.DataFrame(city["buildings"])
    facilities = pd.DataFrame(city["facilities"])

    a,b,c = st.columns(3)

    a.metric("Buildings", len(buildings))
    b.metric("Facilities", len(facilities))
    c.metric(
        "Average Building Height",
        f'{buildings["height"].mean():.1f} m'
    )

    st.markdown("## Public Facilities")

    st.dataframe(
        facilities[["name", "type"]],
        width="stretch",
        hide_index=True
    )


# --------------------------------------------------
# ANALYTICS
# --------------------------------------------------

elif page == "Analytics":

    header(
        "CITY ANALYTICS",
        "Urban infrastructure and simulated movement statistics"
    )

    buildings = pd.DataFrame(city["buildings"])

    a,b = st.columns(2)

    with a:

        fig = px.histogram(
            buildings,
            x="height",
            nbins=15,
            title="Building Height Distribution",
            template="plotly_dark"
        )

        st.plotly_chart(fig, use_container_width=True)

    with b:

        fig = px.pie(
            pd.DataFrame(vehicles),
            names="type",
            title="Vehicle Composition",
            template="plotly_dark"
        )

        st.plotly_chart(fig, use_container_width=True)

    st.markdown("## Simulation Metrics")

    metrics = pd.DataFrame({
        "Metric": [
            "Active Vehicles",
            "Pedestrians",
            "Traffic Signals",
            "Buildings",
            "Facilities"
        ],
        "Value": [
            len(vehicles),
            len(pedestrians),
            len(signals),
            len(city["buildings"]),
            len(city["facilities"])
        ]
    })

    st.dataframe(
        metrics,
        width="stretch",
        hide_index=True
    )


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()

st.markdown(
    """
    <div style="text-align:center;color:#7298b2;font-size:11px">
        NOVACITY | 3D URBAN DIGITAL TWIN |
        TRAFFIC · INFRASTRUCTURE · MOBILITY · ENVIRONMENT
    </div>
    """,
    unsafe_allow_html=True
)