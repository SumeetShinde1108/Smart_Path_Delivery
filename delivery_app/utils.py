from datetime import date
from ortools.constraint_solver import routing_enums_pb2, pywrapcp
from django.contrib.gis.geos import Point
from math import radians, sin, cos, sqrt, atan2
from delivery_app.models import Delivery, Vehicle, Store, Order


def haversine_distance(p1, p2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = radians(p1.y), radians(p1.x), radians(p2.y), radians(p2.x)
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def routing_data(store, orders, vehicles):
    if not orders or not vehicles:
        raise ValueError("ERROR: Orders or vehicles cannot be empty.")
    if not isinstance(store.location.point, Point):
        raise ValueError("ERROR: Store location must be a valid Point object.")

    locations = [store.location.point] + [o.delivery_location.point for o in orders]
    distance_matrix = [
        [int(haversine_distance(loc1, loc2) * 1000) for loc2 in locations]
        for loc1 in locations
    ]
    vehicle_capacities = [int(v.capacity) for v in vehicles]
    vehicle_speeds = [v.average_speed for v in vehicles]
    demands = [0] + [int(o.weight) for o in orders]

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
        raise ValueError("ERROR: No orders available for delivery")

    vehicles.sort(key=lambda v: (v.capacity, v.average_speed), reverse=True)
    existing_delivery = Delivery.objects.filter(date_of_delivery=delivery_date).first()
    delivery = existing_delivery or Delivery.objects.create(
        store=store,
        date_of_delivery=delivery_date,
        total_weight=sum(o.weight for o in orders),
    )

    data = routing_data(store, orders, vehicles)
    manager = pywrapcp.RoutingIndexManager(
        len(data["distance_matrix"]), data["num_vehicles"], data["depot"]
    )
    routing = pywrapcp.RoutingModel(manager)

    def time_callback(f_idx, t_idx):
        return int(
            (
                data["distance_matrix"][manager.IndexToNode(f_idx)][
                    manager.IndexToNode(t_idx)
                ]
                / 1000
            )
            / data["vehicle_speeds"][0]
            * 3600
        )

    transit_idx = routing.RegisterTransitCallback(time_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_idx)

    def demand_callback(idx):
        return data["demands"][manager.IndexToNode(idx)]

    demand_idx = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_idx, 0, data["vehicle_capacities"], True, "Capacity"
    )
    routing.AddDimension(transit_idx, 0, 8 * 100000, True, "Time")

    search_params = pywrapcp.DefaultRoutingSearchParameters()
    search_params.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_params.time_limit.seconds = 1

    solution = routing.SolveWithParameters(search_params)
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
        route, route_distance = [], 0

        while not routing.IsEnd(index):
            route.append(manager.IndexToNode(index))
            prev_idx = index
            index = solution.Value(routing.NextVar(index))
            route_distance += data["distance_matrix"][manager.IndexToNode(prev_idx)][
                manager.IndexToNode(index)
            ]

        route.append(manager.IndexToNode(index))
        assigned_order_ids = [orders[i - 1].id for i in route[1:-1]]
        mapped_route = ["Wharehouse" if i == 0 else orders[i - 1].order_id for i in route]

        if assigned_order_ids:
            routes.append(
                {
                    "vehicle_no": vehicles[vehicle_id].vehicle_no,
                    "average_speed":vehicles[vehicle_id].average_speed,
                    "capacity":vehicles[vehicle_id].capacity,
                    "route_distance_km": route_distance / 1000,
                    "route": mapped_route,
                }
            )

            for order_id in assigned_order_ids:
                order = Order.objects.get(id=order_id)
                order.vehicle = vehicles[vehicle_id]
                order.delivery = delivery
                order.save()

        total_distance += route_distance

    return {"vehicle_routes": routes, "total_distance_km": total_distance/1000 }
