DISTRICTS = {
    "Greenfield": {
        "type": "residential",
        "population": 12000,
        "coordinates": (0, 0),
        "center": (0, 0),
        "color": "#42c98a",
        "description": "Residential neighbourhood",
    },

    "TechPark": {
        "type": "commercial",
        "population": 8000,
        "coordinates": (5, 5),
        "center": (5, 5),
        "color": "#45a9ff",
        "description": "Technology and commercial hub",
    },

    "IndustrialZone": {
        "type": "industrial",
        "population": 5000,
        "coordinates": (10, 0),
        "center": (10, 0),
        "color": "#f0a34a",
        "description": "Industrial and logistics zone",
    },
}


DISTRICT_CONNECTIONS = [
    ("Greenfield", "TechPark"),
    ("TechPark", "IndustrialZone"),
    ("Greenfield", "IndustrialZone"),
]


ROAD_TYPES = {
    "highway": {
        "speed_limit": 80,
        "capacity": 1800,
        "lanes": 4,
        "width": 4,
    },

    "arterial": {
        "speed_limit": 60,
        "capacity": 1200,
        "lanes": 3,
        "width": 3,
    },

    "collector": {
        "speed_limit": 40,
        "capacity": 700,
        "lanes": 2,
        "width": 2,
    },

    "local": {
        "speed_limit": 25,
        "capacity": 350,
        "lanes": 1,
        "width": 1,
    },
}