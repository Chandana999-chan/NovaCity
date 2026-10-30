import networkx as nx
import plotly.graph_objects as go

EVENT_TYPES = ["Normal Conditions", "Road Closure", "Traffic Accident", "Flood"]


def get_coordinates(data):
    """Support both sample-city and NovaCity node formats."""
    if "pos" in data:
        return data["pos"]
    return data["x"], data["y"]


def create_city_map(graph):
    fig = go.Figure()

    for u, v, data in graph.edges(data=True):
        x1, y1 = get_coordinates(graph.nodes[u])
        x2, y2 = get_coordinates(graph.nodes[v])
        closed = data.get("closed", False)
        fig.add_trace(go.Scatter(
            x=[x1, x2],
            y=[y1, y2],
            mode="lines",
            line=dict(
                color="red" if closed else "#38bdf8",
                width=4 if closed else 2
            ),
            hoverinfo="text",
            text=f"{u} - {v}",
            showlegend=False
        ))

    node_x = []
    node_y = []
    node_names = []
    for node, data in graph.nodes(data=True):
        x, y = get_coordinates(data)
        node_x.append(x)
        node_y.append(y)
        node_names.append(node)

    fig.add_trace(go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=node_names,
        textposition="top center",
        marker=dict(
            size=17,
            color="#22c55e",
            line=dict(width=2, color="white")
        ),
        name="City Junctions"
    ))
    fig.update_layout(
        title="NOVACITY | LIVE ROAD NETWORK",
        template="plotly_dark",
        height=550,
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        plot_bgcolor="#0b1220",
        paper_bgcolor="#0b1220"
    )
    return fig


def build_city():
    origin_lon, origin_lat = 77.58, 12.96

    def ll(x, y):
        return [origin_lon + x * 0.00105, origin_lat + y * 0.00105]

    graph = nx.grid_2d_graph(5, 5)
    nodes = {(x, y): f"J{x}{y}" for x, y in graph.nodes}
    roads = []
    for (x, y), (xx, yy) in graph.edges:
        u, v = nodes[(x, y)], nodes[(xx, yy)]
        roads.append({
            "id": f"{u}-{v}",
            "u": u,
            "v": v,
            "path": [ll(x, y), ll(xx, yy)],
            "base_minutes": round(3.2 + ((x + y + xx + yy) % 4) * 0.7, 1),
            "capacity": 90 + ((x * 3 + y) % 5) * 20
        })

    buildings = []
    types = [
        "Residential", "Commercial", "Residential", "Office",
        "Mixed Use", "Residential", "Industrial", "Retail"
    ]
    districts = ["Old Town", "Central", "Tech Park", "Riverside"]
    for i in range(7):
        for j in range(7):
            x = 0.35 + i * 0.62
            y = 0.35 + j * 0.62
            kind = types[(i * 3 + j * 5) % len(types)]
            floors = 3 + ((i * 7 + j * 3) % 19)
            width, depth = 0.00025, 0.00024
            lon, lat = ll(x, y)
            polygon = [
                [lon - width, lat - depth],
                [lon + width, lat - depth],
                [lon + width, lat + depth],
                [lon - width, lat + depth]
            ]
            buildings.append({
                "name": f"{kind} Block {i + 1}-{j + 1}",
                "type": kind,
                "floors": floors,
                "height_m": floors * 3.4,
                "district": districts[(i + j) % len(districts)],
                "polygon": polygon,
                "centroid": ll(x, y)
            })

    specs = [
        ("Nova General Hospital", "Hospital", 1.0, 1.0, 34),
        ("East Medical Centre", "Hospital", 3.0, 3.0, 22),
        ("Central School", "School", 2.0, 1.0, 18),
        ("Nova Institute", "School", 4.0, 2.0, 20),
        ("Central Bus Terminal", "Bus Terminal", 2.0, 2.0, 12),
        ("Fire & Rescue HQ", "Fire Station", 0.0, 4.0, 16),
        ("City Police HQ", "Police", 4.0, 0.0, 15),
        ("Civic Centre", "Government", 2.0, 4.0, 20),
        ("Industrial Hub", "Factory", 4.0, 4.0, 28),
        ("Central Market", "Market", 1.0, 3.0, 10)
    ]
    facilities = [
        {"name": name, "type": kind, "position": ll(x, y), "height_m": height}
        for name, kind, x, y, height in specs
    ]
    return {
        "graph": graph,
        "node_names": nodes,
        "roads": roads,
        "buildings": buildings,
        "facilities": facilities,
        "population": 126500,
        "ll": ll
    }


def available_road_labels(city):
    return [f'{road["u"]} ↔ {road["v"]}' for road in city["roads"]]


def simulate(city, event, road_label, intensity, bus_boost):
    roads = []
    target = road_label.replace(" ↔ ", "-")
    reverse = "-".join(reversed(target.split("-")))
    for road in city["roads"]:
        item = dict(road)
        affected = item["id"] in (target, reverse)
        item["closed"] = False
        item["incident"] = False
        item["congestion_pct"] = 22 + ((len(item["id"]) * 7) % 36)
        if event == "Road Closure" and affected:
            item["closed"] = True
            item["congestion_pct"] = 100
        elif event == "Flood" and affected:
            item["closed"] = True
            item["incident"] = True
            item["congestion_pct"] = 100
        elif event == "Traffic Accident" and affected:
            item["incident"] = True
            item["congestion_pct"] = min(96, 58 + intensity * 8)
        item["congestion_pct"] = max(
            0, min(100, item["congestion_pct"] - bus_boost * 2)
        )
        if item["closed"]:
            item["status"] = "Closed"
        elif item["congestion_pct"] >= 75:
            item["status"] = "Heavy"
        elif item["congestion_pct"] >= 45:
            item["status"] = "Moderate"
        else:
            item["status"] = "Free flow"
        roads.append(item)

    active_graph = nx.Graph()
    active_graph.add_nodes_from(city["graph"].nodes)
    for road in roads:
        if not road["closed"]:
            active_graph.add_edge(
                road["u"],
                road["v"],
                weight=road["base_minutes"] * (1 + road["congestion_pct"] / 160)
            )

    trips = []
    nodes = list(city["graph"].nodes)
    for i in range(32):
        origin = nodes[(i * 7 + 2) % len(nodes)]
        destination = nodes[(i * 11 + 13) % len(nodes)]
        if origin == destination:
            destination = nodes[(i * 11 + 14) % len(nodes)]
        try:
            path = nx.shortest_path(
                active_graph, origin, destination, weight="weight"
            )
            minutes = nx.shortest_path_length(
                active_graph, origin, destination, weight="weight"
            ) * (1 - bus_boost * 0.025)
            trips.append({
                "origin": origin,
                "destination": destination,
                "route": " → ".join(path),
                "minutes": round(minutes, 1),
                "status": "Rerouted" if len(path) > 4 else "Connected"
            })
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            trips.append({
                "origin": origin,
                "destination": destination,
                "route": "No available route",
                "minutes": None,
                "status": "Disrupted"
            })
    return {"roads": roads, "active_graph": active_graph, "trips": trips, "event": event}


def city_summary(city, scenario):
    times = [
        trip["minutes"] for trip in scenario["trips"]
        if trip["minutes"] is not None
    ]
    disrupted = sum(trip["minutes"] is None for trip in scenario["trips"])
    average = sum(times) / len(times) if times else 0
    base_times = [road["base_minutes"] * 1.2 for road in city["roads"]]
    base_average = sum(base_times) / len(base_times) * 2.1 if base_times else average
    congestion = sum(road["congestion_pct"] for road in scenario["roads"]) / len(
        scenario["roads"]
    )
    closed = sum(road["closed"] for road in scenario["roads"])
    heavy = sum(road["status"] == "Heavy" for road in scenario["roads"])
    critical = sum(
        road["status"] in ("Heavy", "Closed") for road in scenario["roads"]
    )
    health = max(
        0,
        100 - congestion * 0.35
        - (disrupted / len(scenario["trips"]) * 100 * 0.4)
        - closed * 2
    )
    return {
        "population": city["population"],
        "avg_time": average,
        "delay": average - base_average,
        "health": health,
        "congestion": congestion,
        "disrupted": disrupted,
        "closed_roads": closed,
        "critical_roads": critical,
        "hospital_access": 100 if any(
            node in scenario["active_graph"]
            for node in scenario["active_graph"].nodes
        ) else 0,
        "road_counts": {
            "Free flow": sum(
                road["status"] == "Free flow" for road in scenario["roads"]
            ),
            "Moderate": sum(
                road["status"] == "Moderate" for road in scenario["roads"]
            ),
            "Heavy": heavy,
            "Closed": closed
        }
    }


def road_table(city, scenario):
    import pandas as pd

    return pd.DataFrame([{
        "road": f'{road["u"]} ↔ {road["v"]}',
        "status": road["status"],
        "congestion_pct": road["congestion_pct"],
        "travel_time_min": road["base_minutes"],
        "capacity_vehicles_hr": road["capacity"],
        "incident": road["incident"]
    } for road in scenario["roads"]])


def facility_table(city):
    import pandas as pd

    return pd.DataFrame([{
        "name": facility["name"],
        "type": facility["type"],
        "height_m": facility["height_m"]
    } for facility in city["facilities"]])
