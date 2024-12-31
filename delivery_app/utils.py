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


def allocate_vehicles_to_deliveries():
    pending_deliveries = Delivery.objects.filter(vehicles__isnull=True)

    for delivery in pending_deliveries:
        try:
            vehicles = Vehicle.objects.all().order_by("-capacity", "-average_speed")

            allocated_vehicles = []
            remaining_weight = delivery.total_weight

            for vehicle in vehicles:
                if remaining_weight <= 0:
                    break
                if vehicle.capacity > 0:
                    allocated_vehicles.append(vehicle)
                    remaining_weight -= vehicle.capacity

            if remaining_weight > 0:
                raise ValueError("Not enough vehicle capacity to handle the delivery.")
            delivery.vehicles.set(allocated_vehicles)
            delivery.save()

        except Exception as e:
            print(f"Error allocating vehicles for delivery {delivery.id}: {str(e)}")


def create_delivery(store, orders, vehicles, date_of_delivery):
    if not orders:
        raise ValueError("No orders provided for delivery.")

    if not vehicles:
        raise ValueError("No vehicles available for delivery.")

    total_weight = sum(order.weight for order in orders)
    try:
        allocated_vehicles = allocate_vehicles_for_delivery(total_weight, vehicles)
    except ValueError as e:
        raise ValueError(f"Vehicle allocation failed: {str(e)}")

    delivery = Delivery.objects.create(
        store=store, total_weight=total_weight, date_of_delivery=date_of_delivery
    )
    delivery.vehicles.set(allocated_vehicles)

    try:
        optimal_route = calculate_optimal_route(
            [order.delivery_location for order in orders], store.location
        )

    except Exception as e:
        raise ValueError(f"Route optimization failed: {str(e)}")

    return delivery, allocated_vehicles, optimal_route
