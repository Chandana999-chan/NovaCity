import random
import pydeck as pdk

# ---------------------------------------------------------
# NOVACITY 3D SCENE ENGINE
# ---------------------------------------------------------

CENTER_LAT = 12.963
CENTER_LON = 77.585

random.seed(42)


def geo(x, y):
    return [
        CENTER_LON + x * 0.00065,
        CENTER_LAT + y * 0.00065
    ]


# ---------------------------------------------------------
# BUILDING GENERATOR
# ---------------------------------------------------------

def generate_buildings():

    buildings = []

    building_types = [
        "Residential",
        "Residential",
        "Commercial",
        "Office",
        "Mixed Use",
        "Industrial",
        "Hotel"
    ]

    for bx in range(10):
        for by in range(10):

            # Multiple buildings in each city block
            count = random.randint(3, 6)

            for _ in range(count):

                x = bx + random.uniform(0.12, 0.83)
                y = by + random.uniform(0.12, 0.83)

                width = random.uniform(0.12, 0.30)
                depth = random.uniform(0.12, 0.30)

                lon, lat = geo(x, y)

                polygon = [
                    [lon - width * 0.00065, lat - depth * 0.00065],
                    [lon + width * 0.00065, lat - depth * 0.00065],
                    [lon + width * 0.00065, lat + depth * 0.00065],
                    [lon - width * 0.00065, lat + depth * 0.00065]
                ]

                kind = random.choice(building_types)

                floors = random.randint(3, 35)

                height = floors * 3.5

                if kind == "Office":
                    color = [42, 135, 185, 245]

                elif kind == "Commercial":
                    color = [40, 165, 190, 245]

                elif kind == "Industrial":
                    color = [160, 120, 95, 245]

                elif kind == "Hotel":
                    color = [130, 100, 190, 245]

                elif kind == "Mixed Use":
                    color = [70, 125, 155, 245]

                else:
                    color = [45, 90, 125, 240]

                buildings.append({
                    "name": f"{kind} Building",
                    "type": kind,
                    "height": height,
                    "floors": floors,
                    "polygon": polygon,
                    "color": color
                })

    return buildings


# ---------------------------------------------------------
# ROAD GENERATOR
# ---------------------------------------------------------

def generate_roads():

    roads = []

    # Main horizontal and vertical roads
    for i in range(11):

        # Horizontal roads
        path = [
            geo(0, i),
            geo(10, i)
        ]

        roads.append({
            "name": f"Main Avenue {i + 1}",
            "type": "Primary",
            "path": path,
            "width": 13,
            "status": "Free Flow",
            "congestion": random.randint(10, 35)
        })

        # Vertical roads
        path = [
            geo(i, 0),
            geo(i, 10)
        ]

        roads.append({
            "name": f"Central Boulevard {i + 1}",
            "type": "Primary",
            "path": path,
            "width": 13,
            "status": "Free Flow",
            "congestion": random.randint(10, 35)
        })

    # Secondary streets
    for x in range(10):

        for y in range(10):

            if x < 9:

                roads.append({
                    "name": f"Street {x}-{y}",
                    "type": "Secondary",
                    "path": [
                        geo(x + 0.5, y + 0.5),
                        geo(x + 1.5, y + 0.5)
                    ],
                    "width": 5,
                    "status": "Moderate",
                    "congestion": random.randint(25, 60)
                })

            if y < 9:

                roads.append({
                    "name": f"Lane {x}-{y}",
                    "type": "Secondary",
                    "path": [
                        geo(x + 0.5, y + 0.5),
                        geo(x + 0.5, y + 1.5)
                    ],
                    "width": 5,
                    "status": "Moderate",
                    "congestion": random.randint(25, 60)
                })

    return roads


# ---------------------------------------------------------
# FACILITY GENERATOR
# ---------------------------------------------------------

def generate_facilities():

    facilities = [

        ("Nova General Hospital", "Hospital", 2, 2),
        ("City Medical Centre", "Hospital", 8, 7),

        ("Central School", "School", 3, 6),
        ("Nova University", "School", 7, 3),

        ("Central Bus Terminal", "Transport", 5, 5),
        ("Metro Interchange", "Transport", 8, 5),

        ("Police Headquarters", "Police", 1, 8),
        ("Fire and Rescue Centre", "Fire", 8, 1),

        ("Municipal Corporation", "Government", 4, 8),
        ("Industrial Research Park", "Industrial", 9, 9),

        ("Central Shopping Mall", "Commercial", 5, 2),
        ("Convention Centre", "Commercial", 3, 8)
    ]

    result = []

    colors = {
        "Hospital": [255, 60, 95, 255],
        "School": [170, 120, 255, 255],
        "Transport": [255, 195, 65, 255],
        "Police": [70, 155, 255, 255],
        "Fire": [255, 100, 55, 255],
        "Government": [70, 220, 205, 255],
        "Industrial": [200, 150, 95, 255],
        "Commercial": [255, 125, 205, 255]
    }

    for name, kind, x, y in facilities:

        result.append({
            "name": name,
            "type": kind,
            "position": geo(x, y),
            "height": random.randint(25, 60),
            "color": colors[kind]
        })

    return result


# ---------------------------------------------------------
# PARKS AND GREEN SPACES
# ---------------------------------------------------------

def generate_parks():

    parks = []

    for x, y in [(1, 4), (5, 8), (8, 4), (3, 1)]:

        lon, lat = geo(x, y)

        parks.append({
            "name": "Urban Green Park",
            "polygon": [
                [lon - 0.0002, lat - 0.0002],
                [lon + 0.0002, lat - 0.0002],
                [lon + 0.0002, lat + 0.0002],
                [lon - 0.0002, lat + 0.0002]
            ]
        })

    return parks


# ---------------------------------------------------------
# DEMO CITY STATE
# ---------------------------------------------------------

def create_demo_city():

    return {
        "buildings": generate_buildings(),
        "roads": generate_roads(),
        "facilities": generate_facilities(),
        "parks": generate_parks(),
        "vehicles": [],
        "population": 126500
    }


# ---------------------------------------------------------
# COLOUR MAPPING
# ---------------------------------------------------------

ROAD_COLORS = {
    "Free Flow": [35, 220, 150, 255],
    "Moderate": [40, 175, 255, 255],
    "Heavy": [255, 180, 45, 255],
    "Closed": [255, 55, 85, 255]
}


# ---------------------------------------------------------
# 3D SCENE RENDERER
# ---------------------------------------------------------

def render_city_scene(city_state):

    layers = []

    # BUILDINGS

    building_data = city_state["buildings"]

    layers.append(
        pdk.Layer(
            "PolygonLayer",
            building_data,
            get_polygon="polygon",
            get_elevation="height",
            get_fill_color="color",
            get_line_color=[100, 200, 245, 180],
            extruded=True,
            wireframe=True,
            elevation_scale=1,
            pickable=True,
            auto_highlight=True
        )
    )

    # PARKS

    layers.append(
        pdk.Layer(
            "PolygonLayer",
            city_state["parks"],
            get_polygon="polygon",
            get_fill_color=[30, 130, 90, 210],
            get_line_color=[80, 230, 150, 230],
            extruded=False,
            pickable=True
        )
    )

    # ROADS

    road_data = []

    for road in city_state["roads"]:

        item = dict(road)

        item["color"] = ROAD_COLORS.get(
            road["status"],
            ROAD_COLORS["Moderate"]
        )

        road_data.append(item)

    layers.append(
        pdk.Layer(
            "PathLayer",
            road_data,
            get_path="path",
            get_color="color",
            get_width="width",
            width_min_pixels=2,
            width_max_pixels=12,
            pickable=True,
            cap_rounded=True,
            joint_rounded=True
        )
    )

    # LANDMARKS

    layers.append(
        pdk.Layer(
            "ColumnLayer",
            city_state["facilities"],
            get_position="position",
            get_elevation="height",
            get_fill_color="color",
            radius=65,
            elevation_scale=2,
            extruded=True,
            pickable=True,
            auto_highlight=True
        )
    )

    # VEHICLES

    if city_state.get("vehicles"):

        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                city_state["vehicles"],
                get_position="position",
                get_fill_color="color",
                get_radius=25,
                radius_min_pixels=4,
                radius_max_pixels=10,
                pickable=True
            )
        )

    # CAMERA

    view = pdk.ViewState(
        latitude=CENTER_LAT + 0.003,
        longitude=CENTER_LON + 0.003,
        zoom=14.2,
        pitch=60,
        bearing=-20
    )

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view,
        map_style=(
            "https://basemaps.cartocdn.com/gl/"
            "dark-matter-gl-style/style.json"
        ),
        tooltip={
            "html": """
                <div style="padding:10px">
                    <b>{name}</b><br/>
                    Type: {type}<br/>
                    Floors: {floors}<br/>
                    Height: {height} m<br/>
                    Status: {status}<br/>
                    Congestion: {congestion}%
                </div>
            """,
            "style": {
                "backgroundColor": "#0b2035",
                "color": "#ffffff",
                "border": "1px solid #38bdf8"
            }
        }
    )

    return deck