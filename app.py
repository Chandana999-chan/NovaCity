import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.visualization.city_scene import (
    create_demo_city,
    render_city_scene
)

st.set_page_config(
    page_title="NovaCity | Urban Intelligence",
    page_icon="🏙️",
    layout="wide"
)

# ---------------------------------------------------------
# DESIGN SYSTEM
# ---------------------------------------------------------

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

* {
    font-family: Inter, sans-serif;
}

.stApp {
    background:
      radial-gradient(ellipse at 48% 0%, #173d59 0%, transparent 48%),
      linear-gradient(130deg, #050d18, #091a2a 55%, #071321);
    color: #edf7ff;
}

.block-container {
    max-width: 1900px;
    padding: 1rem 1.5rem;
}

[data-testid="stSidebar"] {
    background: rgba(5, 18, 32, .97);
    border-right: 1px solid rgba(80,190,230,.2);
}

[data-testid="stMetric"] {
    background: linear-gradient(145deg,
      rgba(28,70,100,.75),
      rgba(8,24,42,.92));
    border: 1px solid rgba(100,190,240,.23);
    padding: 16px;
    border-radius: 15px;
    box-shadow: 0 10px 30px rgba(0,0,0,.25);
}

[data-testid="stMetricLabel"] {
    color: #91b2ca;
    font-size: 11px;
    font-weight: 600;
}

[data-testid="stMetricValue"] {
    color: #ffffff;
    font-size: 25px;
    font-weight: 800;
}

.glass {
    background: linear-gradient(
        145deg,
        rgba(25,65,95,.72),
        rgba(8,24,42,.85)
    );
    border: 1px solid rgba(95,190,230,.23);
    border-radius: 17px;
    padding: 18px;
    backdrop-filter: blur(18px);
    box-shadow: 0 12px 35px rgba(0,0,0,.28);
    margin-bottom: 15px;
}

.eyebrow {
    color: #43d3f2;
    font-size: 10px;
    letter-spacing: 2px;
    font-weight: 800;
}

.muted {
    color: #91aabd;
    font-size: 12px;
}

.status {
    display: inline-block;
    padding: 5px 10px;
    border-radius: 20px;
    background: rgba(30,210,150,.14);
    color: #43e5b0;
    font-size: 11px;
    border: 1px solid rgba(30,210,150,.25);
}

h1 {
    font-weight: 800 !important;
    font-size: 30px !important;
}

h2, h3 {
    color: #eaf7ff !important;
}

hr {
    border-color: rgba(110,180,220,.17);
}

.stButton button {
    background: linear-gradient(100deg,#12516e,#087e9a);
    color: white;
    border: 1px solid #299bb9;
    border-radius: 9px;
    font-weight: 600;
}

</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# INITIALIZE CITY
# ---------------------------------------------------------

if "city_state" not in st.session_state:

    st.session_state.city_state = create_demo_city()

city = st.session_state.city_state


# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------

with st.sidebar:

    st.markdown("# 🏙 NOVACITY")

    st.markdown(
        '<div class="eyebrow">URBAN DIGITAL TWIN</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<span class="status">● SYSTEM ONLINE</span>',
        unsafe_allow_html=True
    )

    st.divider()

    page = st.radio(
        "NAVIGATION",
        [
            "Overview",
            "3D City",
            "Mobility",
            "Infrastructure",
            "Facilities",
            "Emergency",
            "Environment",
            "Analytics"
        ]
    )

    st.divider()

    st.markdown("### CITY INFORMATION")

    st.metric("Population", "126.5K")
    st.metric("Buildings", len(city["buildings"]))
    st.metric("Road Segments", len(city["roads"]))
    st.metric("Facilities", len(city["facilities"]))

    st.divider()

    if st.button("Regenerate City", use_container_width=True):

        st.session_state.city_state = create_demo_city()
        st.rerun()

    st.caption("NovaCity · Simulation-ready visualization")


# ---------------------------------------------------------
# COMMON COMPONENTS
# ---------------------------------------------------------

def header(title, description):

    st.markdown(f"# {title}")

    st.markdown(
        f'<div class="muted">{description}</div>',
        unsafe_allow_html=True
    )

    st.divider()


def city_map(height=650):

    scene = render_city_scene(city)

    st.pydeck_chart(
        scene,
        height=height,
        width="stretch"
    )


def glass(title, content):

    st.markdown(
        f"""
        <div class="glass">
            <div class="eyebrow">{title}</div>
            <br/>
            {content}
        </div>
        """,
        unsafe_allow_html=True
    )


def chart_bar(title, data, x, y):

    fig = px.bar(
        data,
        x=x,
        y=y,
        title=title,
        template="plotly_dark",
        color_discrete_sequence=["#37c8ed"]
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#dcecf7",
        height=310
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ---------------------------------------------------------
# PAGE 1: OVERVIEW
# ---------------------------------------------------------

if page == "Overview":

    header(
        "City Intelligence Command Center",
        "Real-time urban visualization and infrastructure monitoring"
    )

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("Population", "126,500", "+2.4%")
    c2.metric("Buildings", len(city["buildings"]))
    c3.metric("Road Segments", len(city["roads"]))
    c4.metric("Facilities", len(city["facilities"]))
    c5.metric("Green Spaces", len(city["parks"]))

    left, right = st.columns([3.5, 1.1])

    with left:

        glass(
            "LIVE 3D CITY MODEL",
            "Urban landscape · Building geometry · Road infrastructure"
        )

        city_map(650)

    with right:

        glass(
            "CITY STATUS",
            """
            <h2 style="color:#42e7b2">OPERATIONAL</h2>
            <p class="muted">All visualization modules active.</p>
            <hr/>
            <p>🟢 Road network</p>
            <p>🟢 Building registry</p>
            <p>🟢 Public facilities</p>
            <p>🟢 Urban districts</p>
            <p>🟢 3D rendering</p>
            """
        )

        glass(
            "CITY DISTRICTS",
            """
            <h3>10 Urban Zones</h3>
            <p class="muted">Residential · Commercial · Industrial · Central</p>
            """
        )

        glass(
            "INFRASTRUCTURE",
            """
            <h3>12 Key Facilities</h3>
            <p class="muted">Hospitals · Schools · Transport · Emergency services</p>
            """
        )

    st.markdown("## Urban Intelligence")

    a, b = st.columns(2)

    with a:

        building_df = pd.DataFrame(city["buildings"])

        chart_bar(
            "Building Distribution",
            building_df.groupby("type").size().reset_index(name="count"),
            "type",
            "count"
        )

    with b:

        road_df = pd.DataFrame(city["roads"])

        chart_bar(
            "Road Infrastructure",
            road_df.groupby("type").size().reset_index(name="count"),
            "type",
            "count"
        )


# ---------------------------------------------------------
# PAGE 2: 3D CITY
# ---------------------------------------------------------

elif page == "3D City":

    header(
        "NovaCity 3D Explorer",
        "Explore building density, roads, landmarks and urban geometry"
    )

    city_map(760)

    st.markdown("## Building Registry")

    building_df = pd.DataFrame(city["buildings"])

    st.dataframe(
        building_df[["name", "type", "floors", "height"]],
        use_container_width=True,
        hide_index=True
    )


# ---------------------------------------------------------
# PAGE 3: MOBILITY
# ---------------------------------------------------------

elif page == "Mobility":

    header(
        "Mobility and Traffic Intelligence",
        "Road infrastructure and transport network visualization"
    )

    city_map(620)

    roads = pd.DataFrame(city["roads"])

    a, b, c = st.columns(3)

    a.metric("Primary Roads", len(roads[roads["type"] == "Primary"]))
    b.metric("Secondary Roads", len(roads[roads["type"] == "Secondary"]))
    c.metric("Total Segments", len(roads))

    st.markdown("## Road Registry")

    st.dataframe(
        roads[["name", "type", "status", "congestion"]],
        use_container_width=True,
        hide_index=True
    )


# ---------------------------------------------------------
# PAGE 4: INFRASTRUCTURE
# ---------------------------------------------------------

elif page == "Infrastructure":

    header(
        "Urban Infrastructure",
        "Road assets, buildings and city development"
    )

    city_map(620)

    buildings = pd.DataFrame(city["buildings"])

    st.markdown("## Building Statistics")

    a, b, c = st.columns(3)

    a.metric("Total Buildings", len(buildings))
    b.metric("Average Floors", round(buildings["floors"].mean(), 1))
    c.metric("Tallest Building", f'{buildings["height"].max():.0f} m')

    chart_bar(
        "Building Height by Type",
        buildings.groupby("type")["height"].mean().reset_index(),
        "type",
        "height"
    )


# ---------------------------------------------------------
# PAGE 5: FACILITIES
# ---------------------------------------------------------

elif page == "Facilities":

    header(
        "Public Facilities and Services",
        "Essential city infrastructure and facility locations"
    )

    city_map(620)

    facilities = pd.DataFrame(city["facilities"])

    a, b, c, d = st.columns(4)

    a.metric("Hospitals", len(facilities[facilities["type"] == "Hospital"]))
    b.metric("Schools", len(facilities[facilities["type"] == "School"]))
    c.metric("Transport", len(facilities[facilities["type"] == "Transport"]))
    d.metric("Emergency Facilities", len(facilities[
        facilities["type"].isin(["Police", "Fire"])
    ]))

    st.dataframe(
        facilities[["name", "type", "height"]],
        use_container_width=True,
        hide_index=True
    )


# ---------------------------------------------------------
# PAGE 6: EMERGENCY
# ---------------------------------------------------------

elif page == "Emergency":

    header(
        "Emergency Services",
        "Healthcare, police and fire-response infrastructure"
    )

    city_map(650)

    emergency = pd.DataFrame(city["facilities"])

    emergency = emergency[
        emergency["type"].isin([
            "Hospital",
            "Police",
            "Fire"
        ])
    ]

    st.dataframe(
        emergency[["name", "type"]],
        use_container_width=True,
        hide_index=True
    )


# ---------------------------------------------------------
# PAGE 7: ENVIRONMENT
# ---------------------------------------------------------

elif page == "Environment":

    header(
        "Environmental Intelligence",
        "Urban green spaces and sustainability indicators"
    )

    a, b, c, d = st.columns(4)

    a.metric("Green Spaces", len(city["parks"]))
    b.metric("Green Cover", "28%")
    c.metric("Air Quality Index", "42")
    d.metric("Water Reserve", "84%")

    city_map(620)

    st.info(
        "Environmental figures are illustrative data, not live sensor readings."
    )


# ---------------------------------------------------------
# PAGE 8: ANALYTICS
# ---------------------------------------------------------

elif page == "Analytics":

    header(
        "Urban Analytics",
        "Infrastructure distribution and city composition"
    )

    buildings = pd.DataFrame(city["buildings"])
    roads = pd.DataFrame(city["roads"])
    facilities = pd.DataFrame(city["facilities"])

    a, b = st.columns(2)

    with a:

        chart_bar(
            "Buildings by Category",
            buildings.groupby("type").size().reset_index(name="count"),
            "type",
            "count"
        )

    with b:

        chart_bar(
            "Road Network by Classification",
            roads.groupby("type").size().reset_index(name="count"),
            "type",
            "count"
        )

    st.markdown("## Facility Composition")

    fig = px.pie(
        facilities,
        names="type",
        hole=.58,
        template="plotly_dark"
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        height=380
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------

st.divider()

st.markdown(
    """
    <div style="text-align:center;color:#7899b0;font-size:11px">
        NOVACITY · URBAN DIGITAL TWIN · 3D VISUALIZATION PLATFORM
    </div>
    """,
    unsafe_allow_html=True
)