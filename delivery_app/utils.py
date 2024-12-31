from django.contrib.gis.geos import Point
from itertools import permutations
from math import radians, sin, cos, sqrt, atan2
from delivery_app.models import Delivery, Vehicle


def haversine_distance(point1, point2):
    R = 6371.0  
    lat1, lon1 = radians(point1.y), radians(point1.x)
    lat2, lon2 = radians(point2.y), radians(point2.x)

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c


def calculate_optimal_route(locations, store_location):
    all_locations = [store_location] + locations
    location_ids = [loc.id for loc in all_locations]
    best_route = None
    min_distance = float("inf")

    for perm in permutations(location_ids[1:]):
        route = [location_ids[0]] + list(perm) + [location_ids[0]]
        total_distance = 0

        for i in range(len(route) - 1):
            point1 = all_locations[location_ids.index(route[i])].point
            point2 = all_locations[location_ids.index(route[i + 1])].point
            total_distance += haversine_distance(point1, point2)

        if total_distance < min_distance:
            min_distance = total_distance
            best_route = route

    return best_route
