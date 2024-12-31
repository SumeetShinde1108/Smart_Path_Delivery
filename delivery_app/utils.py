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

