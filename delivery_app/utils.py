from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from django.contrib.gis.geos import Point
from math import radians, sin, cos, sqrt, atan2
from delivery_app.models import Delivery, Vehicle, Store, Order
from datetime import date

def haversine_distance(point1, point2):
    R = 6371.0
    lat1, lon1 = radians(point1.y), radians(point1.x)
    lat2, lon2 = radians(point2.y), radians(point2.x)
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def create_data_model(store, orders, vehicles):
    if not orders or not vehicles:
        raise ValueError("Orders or vehicles cannot be empty.")
    locations = [store.location.point] + [order.delivery_location.point for order in orders]
    distance_matrix = []
    for loc1 in locations:
        row = [haversine_distance(loc1, loc2) for loc2 in locations]
        distance_matrix.append(row)
    vehicle_capacities = [int(vehicle.capacity) for vehicle in vehicles]
    vehicle_speeds = [vehicle.average_speed for vehicle in vehicles]
    return {
        "distance_matrix": distance_matrix,
        "num_vehicles": len(vehicles),
        "depot": 0,
        "vehicle_capacities": vehicle_capacities,
        "vehicle_speeds": vehicle_speeds,
    }

def print_solution(data, manager, routing, solution):
    routes = []
    total_distance = 0
    for vehicle_id in range(data["num_vehicles"]):
        index = routing.Start(vehicle_id)
        route = []
        route_distance = 0
        while not routing.IsEnd(index):
            route.append(manager.IndexToNode(index))
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            route_distance += routing.GetArcCostForVehicle(previous_index, index, vehicle_id)
        route.append(manager.IndexToNode(index))
        routes.append({
            "vehicle_id": vehicle_id,
            "route": route,
            "distance": route_distance / 1000
        })
        total_distance += route_distance
    return {"routes": routes, "total_distance": total_distance / 1000}

def assign_vehicles_to_orders(orders, vehicles):
    orders = sorted(orders, key=lambda x: x.weight, reverse=True)
    vehicle_assignments = {vehicle: [] for vehicle in vehicles}
    for order in orders:
        for vehicle in vehicles:
            if vehicle.capacity >= order.weight:
                vehicle_assignments[vehicle].append(order)
                break
    return vehicle_assignments

def assign_routes_to_delivery(store, orders, vehicles, delivery_date):
    if not vehicles:
        raise ValueError("No vehicles available for routing.")
    if not orders:
        raise ValueError("No orders available for delivery.")
    existing_delivery = Delivery.objects.filter(date_of_delivery=delivery_date).first()
    if existing_delivery:
        delivery = existing_delivery
    else:
        delivery = Delivery.objects.create(
            store=store,
            date_of_delivery=delivery_date,
            total_weight=sum(order.weight for order in orders),
        )
    vehicle_assignments = assign_vehicles_to_orders(orders, vehicles)
    assigned_orders = [order for vehicle, assigned_orders in vehicle_assignments.items() for order in assigned_orders]
    delivery.orders.set(assigned_orders)
    delivery.vehicles.set(vehicles)
    data = create_data_model(store, assigned_orders, vehicles)
    manager = pywrapcp.RoutingIndexManager(len(data["distance_matrix"]), data["num_vehicles"], data["depot"])
    routing = pywrapcp.RoutingModel(manager)
    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int(data["distance_matrix"][from_node][to_node] * 1000)
    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
    routing.AddDimension(
        transit_callback_index,
        0,
        1000000,
        True,
        "Distance",
    )
    distance_dimension = routing.GetDimensionOrDie("Distance")
    distance_dimension.SetGlobalSpanCostCoefficient(100)
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
    search_parameters.log_search = True
    search_parameters.time_limit.seconds = 30
    solution = routing.SolveWithParameters(search_parameters)
    if not solution:
        raise ValueError("No solution found for routing problem.")
    solution_data = print_solution(data, manager, routing, solution)
    return solution_data
