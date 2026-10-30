import networkx as nx

def create_sample_city():
    G = nx.Graph()

    locations = {
        "Central": (0, 0),
        "Hospital": (1, 2),
        "School": (3, 2),
        "Office": (4, 0),
        "Market": (3, -2),
        "Factory": (6, 0),
        "Bus Station": (1, -2),
        "Residential": (6, 2)
    }

    for name, position in locations.items():
        G.add_node(name, pos=position)

    roads = [
        ("Central", "Hospital", 4),
        ("Central", "Bus Station", 3),
        ("Central", "Office", 5),
        ("Hospital", "School", 3),
        ("School", "Office", 4),
        ("Office", "Market", 3),
        ("Market", "Bus Station", 4),
        ("Office", "Factory", 5),
        ("Factory", "Residential", 3),
        ("School", "Residential", 6),
        ("Market", "Factory", 5),
        ("Hospital", "Bus Station", 5)
    ]

    for source, destination, time in roads:
        G.add_edge(
            source,
            destination,
            travel_time=time,
            closed=False
        )

    return G


COMMUTERS = [
    ("Residential", "Hospital"),
    ("Residential", "Office"),
    ("Bus Station", "School"),
    ("Market", "Office"),
    ("Hospital", "Factory"),
    ("Central", "Residential"),
    ("School", "Market"),
    ("Bus Station", "Factory"),
    ("Residential", "Market"),
    ("Factory", "Hospital"),
    ("Central", "School"),
    ("Market", "Hospital")
]