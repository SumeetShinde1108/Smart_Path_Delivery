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


def assign_routes_to_delivery(store, orders, vehicles, delivery_date):
    if not vehicles:
        return {"error": "No vehicles available for routing."}
    if not orders:
        return {"error": "No orders available for delivery."}

    vehicles = sorted(vehicles, key=lambda v: v.capacity, reverse=True)

    existing_delivery = Delivery.objects.filter(date_of_delivery=delivery_date).first()
    delivery = existing_delivery or Delivery.objects.create(
        store=store,
        date_of_delivery=delivery_date,
        total_weight=sum(order.weight for order in orders),
    )

    data = create_data_model(store, orders, vehicles)

    print(f"DEBUG: Vehicles count: {len(vehicles)}")
    print(f"DEBUG: Number of orders: {len(orders)}")
    print(f"DEBUG: Distance Matrix: {data['distance_matrix']}")
    print(f"DEBUG: Vehicle Capacities: {data['vehicle_capacities']}")

    manager = pywrapcp.RoutingIndexManager(
        len(data["distance_matrix"]), data["num_vehicles"], data["depot"]
    )
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        distance = data["distance_matrix"][from_node][to_node]
        print(f"Distance from node {from_node} to node {to_node}: {distance} meters")
        return distance

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    def demand_callback(from_index):
        from_node = manager.IndexToNode(from_index)
        return data["demands"][from_node]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index, 0, data["vehicle_capacities"], True, "Capacity"
    )

    def time_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        travel_distance = data["distance_matrix"][from_node][to_node]
        vehicle_id = solution.Value(routing.VehicleVar(from_index))

        if vehicle_id >= len(data["vehicle_speeds"]):
            return travel_distance

        travel_speed = data["vehicle_speeds"][vehicle_id]
        travel_time = int(travel_distance / travel_speed)
        return travel_time

    time_callback_index = routing.RegisterTransitCallback(time_callback)
    max_time = 1_000_000
    routing.AddDimension(time_callback_index, 0, max_time, True, "Time")

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.time_limit.seconds = 30

    solution = routing.SolveWithParameters(search_parameters)

    if solution is None:
        print(
            "DEBUG: No solution found by OR-Tools. The problem might be over-constrained."
        )
        return {
            "error": "No feasible solution found. Adjust vehicle capacities or delivery constraints."
        }

    return assign_vehicles_and_extract_routes(
        data, manager, routing, solution, vehicles, orders, delivery
    )


def assign_vehicles_and_extract_routes(
    data, manager, routing, solution, vehicles, orders, delivery
):
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
            route_distance += routing.GetArcCostForVehicle(
                previous_index, index, vehicle_id
            )

        route.append(manager.IndexToNode(index))
        assigned_order_ids = [orders[i - 1].id for i in route[1:-1]]

        route_distance_km = route_distance / 1000

        if assigned_order_ids:
            routes.append(
                {
                    "vehicle_no": vehicles[vehicle_id].vehicle_no,
                    "assigned_orders": assigned_order_ids,
                    "route_distance_km": route_distance_km,
                }
            )
            for order_id in assigned_order_ids:
                order = Order.objects.get(id=order_id)
                order.vehicle = vehicles[vehicle_id]
                order.delivery = delivery
                order.save()

        total_distance += route_distance

    print("\n SUCCESS: Routing solution generated.")
    print(f"DEBUG: Total Distance = {total_distance / 1000} km")

    return {"vehicle_routes": routes, "total_distance_km": total_distance / 1000}
