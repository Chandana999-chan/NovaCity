import networkx as nx
import math
import time


class VehicleSafetySystem:

    def __init__(self, graph, collision_distance=5.0):

        self.graph = graph
        self.collision_distance = collision_distance

        self.accidents = []
        self.blocked_roads = set()

    def road_key(self, u, v):
        return tuple(sorted((str(u), str(v))))

    def close_road(self, u, v, reason="accident"):

        if not self.graph.has_edge(u, v):
            return False

        self.graph[u][v]["closed"] = True
        self.graph[u][v]["event_type"] = reason

        self.blocked_roads.add(
            self.road_key(u, v)
        )

        return True

    def reopen_road(self, u, v):

        if not self.graph.has_edge(u, v):
            return False

        self.graph[u][v]["closed"] = False
        self.graph[u][v]["event_type"] = "none"

        self.blocked_roads.discard(
            self.road_key(u, v)
        )

        return True

    def calculate_safe_route(self, start, destination):

        if start not in self.graph:
            return []

        if destination not in self.graph:
            return []

        def weight(u, v, data):

            if data.get("closed", False):
                return math.inf

            distance = float(data.get("distance", 1))

            return max(distance, 0.001)

        try:

            return nx.shortest_path(
                self.graph,
                start,
                destination,
                weight=weight
            )

        except (
            nx.NetworkXNoPath,
            nx.NodeNotFound
        ):

            return []

    def detect_collisions(self, vehicles):

        new_accidents = []

        for i in range(len(vehicles)):

            first = vehicles[i]

            if first.get("crashed", False):
                continue

            for j in range(i + 1, len(vehicles)):

                second = vehicles[j]

                if second.get("crashed", False):
                    continue

                # Only vehicles on the same road can collide
                # in this simplified road-based model.

                if first.get("road") != second.get("road"):
                    continue

                p1 = first.get("position")
                p2 = second.get("position")

                if not p1 or not p2:
                    continue

                distance = math.dist(p1, p2)

                if distance <= self.collision_distance:

                    first["crashed"] = True
                    second["crashed"] = True

                    first["speed"] = 0
                    second["speed"] = 0

                    accident = {
                        "type": "accident",
                        "road": first.get("road"),
                        "vehicles": [
                            first.get("id"),
                            second.get("id")
                        ],
                        "severity": "high",
                        "timestamp": time.time()
                    }

                    new_accidents.append(accident)

                    road = first.get("road")

                    if road and len(road) == 2:

                        self.close_road(
                            road[0],
                            road[1],
                            "accident"
                        )

                    break

        self.accidents.extend(new_accidents)

        return new_accidents

    def reroute_vehicle(
        self,
        vehicle,
        current_node,
        destination
    ):

        route = self.calculate_safe_route(
            current_node,
            destination
        )

        if not route:
            vehicle["status"] = "stranded"
            vehicle["speed"] = 0
            return False

        vehicle["route"] = route
        vehicle["route_index"] = 0
        vehicle["status"] = "rerouted"

        return True

    def get_accidents(self):
        return self.accidents