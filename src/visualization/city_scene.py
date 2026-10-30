import math
import random
import pydeck as pdk

CENTER_LAT = 12.963
CENTER_LON = 77.585

random.seed(42)

# --------------------------------------------------
# GEO COORDINATES
# --------------------------------------------------

def geo(x, y):
    return [
        CENTER_LON + x * 0.00065,
        CENTER_LAT + y * 0.00065
    ]


# --------------------------------------------------
# BUILDINGS
# --------------------------------------------------

def generate_buildings():

    buildings = []

    types = [
        "Residential",
        "Commercial",
        "Office Tower",
        "Hotel",
        "Industrial",
        "Shopping Complex"
    ]

    colors = {
        "Residential": [35, 115, 165, 240],
        "Commercial": [20, 190, 210, 245],
        "Office Tower": [100, 125, 255, 245],
        "Hotel": [190, 90, 220, 245],
        "Industrial": [210, 145, 75, 245],
        "Shopping Complex": [40, 205, 165, 245]
    }

    for x in range(10):
        for y in range(10):

            for _ in range(random.randint(3, 5)):

                bx = x + random.uniform(0.12, 0.80)
                by = y + random.uniform(0.12, 0.80)

                width = random.uniform(0.10, 0.24)
                depth = random.uniform(0.10, 0.24)

                lon, lat = geo(bx, by)

                kind = random.choice(types)
                floors = random.randint(4, 38)

                polygon = [
                    geo(bx - width / 2, by - depth / 2),
                    geo(bx + width / 2, by - depth / 2),
                    geo(bx + width / 2, by + depth / 2),
                    geo(bx - width / 2, by + depth / 2)
                ]

                buildings.append({
                    "name": kind + " " + str(len(buildings) + 1),
                    "type": kind,
                    "floors": floors,
                    "height": floors * 3.5,
                    "polygon": polygon,
                    "color": colors[kind]
                })

    return buildings


# --------------------------------------------------
# ROAD NETWORK
# --------------------------------------------------

def generate_roads():

    roads = []

    # Main roads
    for i in range(11):

        roads.append({
            "name": f"North Avenue {i}",
            "type": "Primary",
            "path": [geo(0, i), geo(10, i)],
            "width": 15
        })

        roads.append({
            "name": f"Central Boulevard {i}",
            "type": "Primary",
            "path": [geo(i, 0), geo(i, 10)],
            "width": 15
        })

    # Secondary roads
    for x in range(10):
        for y in range(10):

            roads.append({
                "name": f"Street {x}-{y}",
                "type": "Secondary",
                "path": [
                    geo(x + 0.5, y + 0.5),
                    geo(x + 1, y + 0.5)
                ],
                "width": 7
            })

            roads.append({
                "name": f"Lane {x}-{y}",
                "type": "Secondary",
                "path": [
                    geo(x + 0.5, y + 0.5),
                    geo(x + 0.5, y + 1)
                ],
                "width": 7
            })

    return roads


# --------------------------------------------------
# FACILITIES
# --------------------------------------------------

def generate_facilities():

    items = [
        ("Nova General Hospital", "Hospital", 2, 2),
        ("City Medical Centre", "Hospital", 8, 7),
        ("Central School", "School", 3, 6),
        ("Nova University", "School", 7, 3),
        ("Central Bus Terminal", "Bus Station", 5, 5),
        ("Metro Interchange", "Metro", 8, 5),
        ("Police Headquarters", "Police", 1, 8),
        ("Fire and Rescue Centre", "Fire Station", 8, 1),
        ("Municipal Corporation", "Government", 4, 8),
        ("Central Shopping Mall", "Mall", 5, 2)
    ]

    colors = {
        "Hospital": [255, 55, 95, 255],
        "School": [180, 110, 255, 255],
        "Bus Station": [255, 190, 40, 255],
        "Metro": [40, 210, 240, 255],
        "Police": [60, 145, 255, 255],
        "Fire Station": [255, 85, 45, 255],
        "Government": [40, 220, 180, 255],
        "Mall": [240, 100, 210, 255]
    }

    result = []

    for name, kind, x, y in items:

        result.append({
            "name": name,
            "type": kind,
            "position": geo(x, y),
            "height": 45,
            "color": colors[kind]
        })

    return result


# --------------------------------------------------
# PARKS
# --------------------------------------------------

def generate_parks():

    parks = []

    for x, y in [(1, 4), (5, 8), (8, 4), (3, 1)]:

        parks.append({
            "name": "Nova Green Park",
            "polygon": [
                geo(x, y),
                geo(x + 0.8, y),
                geo(x + 0.8, y + 0.8),
                geo(x, y + 0.8)
            ]
        })

    return parks


# --------------------------------------------------
# TRAFFIC SIGNALS
# --------------------------------------------------

def generate_signals():

    signals = []

    for x in range(1, 10):
        for y in range(1, 10):

            if x % 2 == 0 and y % 2 == 0:

                signals.append({
                    "name": f"Signal {x}-{y}",
                    "position": geo(x, y),
                    "phase": (x + y) % 3
                })

    return signals


# --------------------------------------------------
# CITY INITIALIZATION
# --------------------------------------------------

def create_city():

    return {
        "buildings": generate_buildings(),
        "roads": generate_roads(),
        "facilities": generate_facilities(),
        "parks": generate_parks(),
        "signals": generate_signals()
    }


# --------------------------------------------------
# INTERPOLATION
# --------------------------------------------------

def interpolate(a, b, t):

    return [
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t
    ]


# --------------------------------------------------
# VEHICLE SIMULATION
# --------------------------------------------------

def generate_vehicles(city, tick, density, bus_frequency):

    vehicles = []

    primary_roads = [
        r for r in city["roads"]
        if r["type"] == "Primary"
    ]

    count = int(density * 1.5)

    for i in range(count):

        road = primary_roads[i % len(primary_roads)]

        path = road["path"]

        # Cycle through road path
        phase = (tick * 0.012 + i * 0.11) % 1

        position = interpolate(
            path[0],
            path[1],
            phase
        )

        kind = "Car"
        color = [30, 210, 255, 255]
        radius = 35

        # Introduce buses at configurable frequency
        if i % max(2, 12 - bus_frequency) == 0:

            kind = "Bus"
            color = [255, 185, 35, 255]
            radius = 75

        # Emergency vehicles
        if i % 23 == 0:

            kind = "Emergency"
            color = [255, 55, 75, 255]
            radius = 55

        vehicles.append({
            "name": f"{kind} {i + 1}",
            "type": kind,
            "position": position,
            "color": color,
            "radius": radius
        })

    return vehicles


# --------------------------------------------------
# PEDESTRIAN SIMULATION
# --------------------------------------------------

def generate_pedestrians(city, tick, population):

    pedestrians = []

    count = population

    for i in range(count):

        # Pedestrians move along horizontal sidewalks
        lane = i % 10
        start_x = (i * 0.37) % 10

        movement = (tick * 0.003 + i * 0.07) % 1

        x = (start_x + movement * 2) % 10
        y = lane + 0.12

        position = geo(x, y)

        pedestrians.append({
            "name": f"Pedestrian {i + 1}",
            "position": position,
            "color": [190, 110, 255, 255],
            "radius": 15
        })

    return pedestrians


# --------------------------------------------------
# TRAFFIC LIGHT STATES
# --------------------------------------------------

def update_signals(city, tick, signal_duration):

    result = []

    for signal in city["signals"]:

        phase = int(
            (tick // max(1, signal_duration) + signal["phase"]) % 3
        )

        if phase == 0:
            state = "GREEN"
            color = [20, 255, 100, 255]

        elif phase == 1:
            state = "YELLOW"
            color = [255, 210, 20, 255]

        else:
            state = "RED"
            color = [255, 40, 65, 255]

        result.append({
            **signal,
            "state": state,
            "color": color
        })

    return result


# --------------------------------------------------
# 3D MAP
# --------------------------------------------------

def render_city(
    city,
    vehicles,
    pedestrians,
    signals,
    bearing=0,
    pitch=65,
    zoom=14.5
):

    layers = []

    # Building geometry
    layers.append(
        pdk.Layer(
            "PolygonLayer",
            city["buildings"],
            get_polygon="polygon",
            get_elevation="height",
            get_fill_color="color",
            get_line_color=[110, 220, 255, 210],
            extruded=True,
            wireframe=True,
            elevation_scale=1,
            pickable=True,
            auto_highlight=True
        )
    )

    # Green spaces
    layers.append(
        pdk.Layer(
            "PolygonLayer",
            city["parks"],
            get_polygon="polygon",
            get_fill_color=[20, 115, 75, 230],
            get_line_color=[50, 255, 160, 255],
            extruded=False,
            pickable=True
        )
    )

    # Road surfaces - dark thick lines
    layers.append(
        pdk.Layer(
            "PathLayer",
            city["roads"],
            get_path="path",
            get_color=[15, 25, 38, 255],
            get_width="width",
            width_min_pixels=5,
            width_max_pixels=22,
            pickable=True
        )
    )

    # Road neon edge / traffic lanes
    layers.append(
        pdk.Layer(
            "PathLayer",
            city["roads"],
            get_path="path",
            get_color=[65, 165, 205, 210],
            get_width=2,
            width_min_pixels=2,
            width_max_pixels=3
        )
    )

    # Lane markings
    layers.append(
        pdk.Layer(
            "PathLayer",
            city["roads"],
            get_path="path",
            get_color=[230, 240, 255, 180],
            get_width=1,
            width_min_pixels=1,
            width_max_pixels=2
        )
    )

    # Facilities
    layers.append(
        pdk.Layer(
            "ColumnLayer",
            city["facilities"],
            get_position="position",
            get_elevation="height",
            get_fill_color="color",
            radius=55,
            elevation_scale=1,
            extruded=True,
            pickable=True
        )
    )

    # Traffic lights
    layers.append(
        pdk.Layer(
            "ScatterplotLayer",
            signals,
            get_position="position",
            get_fill_color="color",
            get_radius=40,
            radius_min_pixels=6,
            radius_max_pixels=14,
            pickable=True
        )
    )

    # Vehicles
    layers.append(
        pdk.Layer(
            "ScatterplotLayer",
            vehicles,
            get_position="position",
            get_fill_color="color",
            get_radius="radius",
            radius_min_pixels=4,
            radius_max_pixels=13,
            pickable=True
        )
    )

    # Pedestrians
    layers.append(
        pdk.Layer(
            "ScatterplotLayer",
            pedestrians,
            get_position="position",
            get_fill_color="color",
            get_radius="radius",
            radius_min_pixels=2,
            radius_max_pixels=6,
            pickable=True
        )
    )

    view = pdk.ViewState(
        latitude=CENTER_LAT + 0.003,
        longitude=CENTER_LON + 0.003,
        zoom=zoom,
        pitch=pitch,
        bearing=bearing
    )

    return pdk.Deck(
        layers=layers,
        initial_view_state=view,
        map_style=(
            "https://basemaps.cartocdn.com/gl/"
            "dark-matter-gl-style/style.json"
        ),
        tooltip={
            "html": """
                <b>{name}</b><br/>
                Type: {type}<br/>
                State: {state}
            """,
            "style": {
                "backgroundColor": "#071b30",
                "color": "white"
            }
        }
    )