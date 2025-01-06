from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from django.contrib.gis.geos import Point
from math import radians, sin, cos, sqrt, atan2
from delivery_app.models import Delivery, Vehicle, Store, Order
from datetime import date


def haversine_distance(point1, point2):
    if not isinstance(point1, Point) or not isinstance(point2, Point):
        raise ValueError(
            "ERROR: Both inputs to haversine_distance must be Point objects."
        )

    R = 6371.0
    lat1, lon1 = radians(point1.y), radians(point1.x)
    lat2, lon2 = radians(point2.y), radians(point2.x)
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


def create_data_model(store, orders, vehicles):
    if not orders or not vehicles:
        raise ValueError("ERROR: Orders or vehicles cannot be empty.")

    if not isinstance(store.location.point, Point):
        raise ValueError("ERROR: Store location must be a valid Point object.")

    for order in orders:
        if not isinstance(order.delivery_location.point, Point):
            raise ValueError(
                f"ERROR: Order {order.id} delivery location must be a valid Point object."
            )

    locations = [store.location.point] + [
        order.delivery_location.point for order in orders
    ]

    distance_matrix = []
    for loc1 in locations:
        row = []
        for loc2 in locations:
            distance = haversine_distance(loc1, loc2)
            row.append(int(distance * 1000))
        distance_matrix.append(row)

    print("DEBUG: Distance Matrix:")
    for row in distance_matrix:
        print(row)

    vehicle_capacities = [int(vehicle.capacity) for vehicle in vehicles]
    vehicle_speeds = [vehicle.average_speed for vehicle in vehicles]

    for vehicle in vehicles:
        if vehicle.average_speed <= 0:
            raise ValueError(
                f"ERROR: Vehicle {vehicle.vehicle_no} has an invalid speed ({vehicle.average_speed} km/h)."
            )
    print("DEBUG: Haversine distances (in km):")
    for loc1 in locations:
        for loc2 in locations:
            distance = haversine_distance(loc1, loc2)
            print(f"From {loc1} to {loc2}: {distance} km")

    demands = [0] + [int(order.weight) for order in orders]

    return {
        "distance_matrix": distance_matrix,
        "num_vehicles": len(vehicles),
        "depot": 0,
        "vehicle_capacities": vehicle_capacities,
        "vehicle_speeds": vehicle_speeds,
        "demands": demands,
    }


