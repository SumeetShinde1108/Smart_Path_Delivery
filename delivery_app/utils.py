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

    vehicle_capacities = [int(vehicle.capacity) for vehicle in vehicles]
    vehicle_speeds = [vehicle.average_speed for vehicle in vehicles]

    for vehicle in vehicles:
        if vehicle.average_speed <= 0:
            raise ValueError(
                f"ERROR: Vehicle {vehicle.vehicle_no} has an invalid speed ({vehicle.average_speed} km/h)."
            )

    demands = [0] + [int(order.weight) for order in orders]

    return {
        "distance_matrix": distance_matrix,
        "num_vehicles": len(vehicles),
        "depot": 0,
        "vehicle_capacities": vehicle_capacities,
        "vehicle_speeds": vehicle_speeds,
        "demands": demands,
        "locations": locations,
    }


def assign_routes_to_delivery(store, orders, vehicles, delivery_date):
    if not vehicles:
        raise ValueError("ERROR: No vehicles available for routing.")
    if not orders:
        raise ValueError("ERROR: No orders available for delivery.")

    vehicles = sorted(vehicles, key=lambda v: v.capacity, reverse=True)

    existing_delivery = Delivery.objects.filter(date_of_delivery=delivery_date).first()
    delivery = existing_delivery or Delivery.objects.create(
        store=store,
        date_of_delivery=delivery_date,
        total_weight=sum(order.weight for order in orders),
    )

    data = create_data_model(store, orders, vehicles)
    manager = pywrapcp.RoutingIndexManager(
        len(data["distance_matrix"]), data["num_vehicles"], data["depot"]
    )
    routing = pywrapcp.RoutingModel(manager)

    def time_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        distance = data["distance_matrix"][from_node][to_node]
        speed = data["vehicle_speeds"][0]
        return int((distance / 1000) / speed * 3600)

    transit_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    def demand_callback(from_index):
        from_node = manager.IndexToNode(from_index)
        return data["demands"][from_node]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index, 0, data["vehicle_capacities"], True, "Capacity"
    )

    max_travel_time = 8 * 3600
    routing.AddDimension(
        transit_callback_index,
        0,
        max_travel_time,
        True,
        "Time",
    )

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.time_limit.seconds = 30

    solution = routing.SolveWithParameters(search_parameters)
    if not solution:
        raise ValueError(
            "ERROR: Routing solution did not generate valid vehicle routes."
        )

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
            route_distance += data["distance_matrix"][
                manager.IndexToNode(previous_index)
            ][manager.IndexToNode(index)]

        route.append(manager.IndexToNode(index))

        assigned_order_ids = [orders[i - 1].id for i in route[1:-1]]

        route_distance_km = route_distance / 1000

        mapped_route = ["Store" if i == 0 else orders[i - 1].id for i in route]

        if assigned_order_ids:
            routes.append(
                {
                    "vehicle_no": vehicles[vehicle_id].vehicle_no,
                    "assigned_orders": assigned_order_ids,
                    "route_distance_km": route_distance_km,
                    "route": mapped_route,
                }
            )
            for order_id in assigned_order_ids:
                order = Order.objects.get(id=order_id)
                order.vehicle = vehicles[vehicle_id]
                order.delivery = delivery
                order.save()

        total_distance += route_distance

    return {"vehicle_routes": routes, "total_distance_km": total_distance / 1000}
