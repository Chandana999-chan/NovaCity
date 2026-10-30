
import numpy as np
import pandas as pd


def generate_commuters(city, num_commuters=500, seed=42):

    if num_commuters <= 0:
        raise ValueError("Number of commuters must be positive.")

    if city.number_of_nodes() == 0:
        raise ValueError("City network cannot be empty.")

    rng = np.random.default_rng(seed)

    # Group junctions by district
    district_junctions = {}

    for junction, details in city.nodes(data=True):
        district = details["district"]

        district_junctions.setdefault(district, []).append(junction)

    districts = list(district_junctions)

    if len(districts) < 2:
        raise ValueError("At least two districts are required.")

    # Commuting destination preferences
    destination_preferences = {
        "Greenfield": ["TechPark", "IndustrialZone"],
        "TechPark": ["Greenfield", "IndustrialZone"],
        "IndustrialZone": ["TechPark", "Greenfield"]
    }

    commuters = []

    for i in range(num_commuters):

        # Select home district
        home_district = rng.choice(
            ["Greenfield", "TechPark", "IndustrialZone"],
            p=[0.45, 0.20, 0.35]
        )

        # Select a different workplace district
        possible_destinations = destination_preferences[
            home_district
        ]

        work_district = rng.choice(possible_destinations)

        # Select home and workplace junctions
        origin = rng.choice(
            district_junctions[home_district]
        )

        destination = rng.choice(
            district_junctions[work_district]
        )

        # Morning departure: 7 AM to 10 AM
        departure_minute = int(
            np.clip(
                rng.normal(510, 40),
                420,
                600
            )
        )

        hours = departure_minute // 60
        minutes = departure_minute % 60

        departure_time = f"{hours:02d}:{minutes:02d}"

        # Transport mode
        transport_mode = rng.choice(
            ["car", "bus"],
            p=[0.70, 0.30]
        )

        commuters.append({
            "commuter_id": f"C{i + 1:03d}",
            "origin": origin,
            "destination": destination,
            "home_district": home_district,
            "work_district": work_district,
            "departure_minute": departure_minute,
            "departure_time": departure_time,
            "transport_mode": transport_mode
        })

    return pd.DataFrame(commuters)


if __name__ == "__main__":

    from src.city.city import create_city

    city = create_city()

    commuters = generate_commuters(city)

    print("NOVACITY COMMUTER GENERATION")
    print("----------------------------")

    print("Total commuters:", len(commuters))

    print("\nTransport distribution:")
    print(commuters["transport_mode"].value_counts())

    print("\nDistrict distribution:")
    print(commuters["home_district"].value_counts())

    print("\nSample commuters:")
    print(commuters.head(10).to_string(index=False))
