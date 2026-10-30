
import networkx as nx

from src.city.districts import DISTRICTS


def create_city():

    city = nx.Graph()

    # Junctions grouped by district
    junctions = {
        # Greenfield
        "J1": ("Greenfield", 0, 0),
        "J2": ("Greenfield", 1, 2),
        "J3": ("Greenfield", 2, 0),
        "J4": ("Greenfield", 3, 2),
        "J5": ("Greenfield", 4, 0),

        # TechPark
        "J6": ("TechPark", 5, 3),
        "J7": ("TechPark", 6, 5),
        "J8": ("TechPark", 7, 3),
        "J9": ("TechPark", 8, 5),
        "J10": ("TechPark", 9, 3),

        # Industrial Zone
        "J11": ("IndustrialZone", 10, 0),
        "J12": ("IndustrialZone", 11, 2),
        "J13": ("IndustrialZone", 12, 0),
        "J14": ("IndustrialZone", 13, 2),
        "J15": ("IndustrialZone", 14, 0),
    }

    # Add junctions
    for junction, (district, x, y) in junctions.items():
        city.add_node(
            junction,
            district=district,
            x=x,
            y=y,
            node_type="junction"
        )

    # Roads: start, end, distance, capacity, speed
    roads = [
        # Greenfield roads
        ("J1", "J2", 2, 800, 35),
        ("J2", "J3", 2, 800, 35),
        ("J3", "J4", 2, 800, 35),
        ("J4", "J5", 2, 800, 35),
        ("J1", "J3", 3, 1200, 50),
        ("J3", "J5", 3, 1200, 50),

        # TechPark roads
        ("J6", "J7", 2, 1500, 50),
        ("J7", "J8", 2, 1500, 50),
        ("J8", "J9", 2, 1500, 50),
        ("J9", "J10", 2, 1500, 50),
        ("J6", "J8", 3, 1800, 60),
        ("J8", "J10", 3, 1800, 60),

        # Industrial roads
        ("J11", "J12", 2, 700, 30),
        ("J12", "J13", 2, 700, 30),
        ("J13", "J14", 2, 700, 30),
        ("J14", "J15", 2, 700, 30),
        ("J11", "J13", 3, 1000, 40),
        ("J13", "J15", 3, 1000, 40),

        # Inter-district connections
        ("J5", "J6", 3, 1800, 60),
        ("J10", "J11", 4, 1500, 50),
        ("J3", "J8", 5, 1200, 45),
        ("J8", "J12", 5, 1000, 40),
    ]

    # Add roads
    for start, end, distance, capacity, speed in roads:
        city.add_edge(
            start,
            end,
            distance=distance,
            capacity=capacity,
            speed=speed,
            traffic=0,
            closed=False
        )

    return city


if __name__ == "__main__":

    city = create_city()

    print("NOVACITY ROAD NETWORK")
    print("---------------------")
    print("Junctions:", city.number_of_nodes())
    print("Roads:", city.number_of_edges())
    print("Connected:", nx.is_connected(city))

    print("\nDistrict distribution:")

    for district in DISTRICTS:
        count = sum(
            1 for _, data in city.nodes(data=True)
            if data["district"] == district
        )
        print(district, ":", count, "junctions")
G=create_city()
print('Distance:', nx.shortest_path_length(G, 'J1', 'J15', weight='distance'), 'km')