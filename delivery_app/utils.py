from datetime import date
from ortools.constraint_solver import routing_enums_pb2, pywrapcp
from django.contrib.gis.geos import Point
from math import radians, sin, cos, sqrt, atan2
from delivery_app.models import Delivery, Vehicle, Store, Order


def haversine_distance(p1, p2):
    """Calculate the haversine distance in kilometers."""
    R = 6371.0
    lat1, lon1, lat2, lon2 = radians(p1.y), radians(p1.x), radians(p2.y), radians(p2.x)
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def routing_data(store, orders, vehicles):
    """Prepare routing data for the OR-Tools solver."""
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
    demands = [0] + [int(o.weight) for o in orders]

    return {
        "distance_matrix": distance_matrix,
        "num_vehicles": len(vehicles),
        "depot": 0,
        "vehicle_capacities": vehicle_capacities,
        "demands": demands,
        "locations": locations,
    }


def assign_routes_to_delivery(store, orders, vehicles, delivery_date, num_variants=3):
    """Assign routes and showcase route variants for a delivery date."""
    if not vehicles:
        raise ValueError("ERROR: No vehicles available for routing.")
    if not orders:
        raise ValueError("ERROR: No orders available for delivery.")

    orders.sort(key=lambda o: o.weight, reverse=True)
    vehicles.sort(key=lambda v: (-v.average_speed, -v.capacity))

    delivery_weight = sum(o.weight for o in orders)
    delivery, _ = Delivery.objects.get_or_create(
        store=store,
        date_of_delivery=delivery_date,
        defaults={"total_weight": delivery_weight},
    )

    data = routing_data(store, orders, vehicles)
    manager = pywrapcp.RoutingIndexManager(
        len(data["distance_matrix"]), data["num_vehicles"], data["depot"]
    )
    routing = pywrapcp.RoutingModel(manager)

    def time_callback(f_idx, t_idx):
        """Time callback function to calculate travel time."""
        return int(
            data["distance_matrix"][manager.IndexToNode(f_idx)][
                manager.IndexToNode(t_idx)
            ]
            / max(v.average_speed for v in vehicles)
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

    variants = []
    strategies = [
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC,
        routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION,
        routing_enums_pb2.FirstSolutionStrategy.SAVINGS,
    ]
    search_params = pywrapcp.DefaultRoutingSearchParameters()
    search_params.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_params.time_limit.seconds = 2

    for i in range(min(num_variants, len(strategies))):
        search_params.first_solution_strategy = strategies[i]
        solution = routing.SolveWithParameters(search_params)

        if solution:
            variant = assign_vehicles_and_extract_routes(
                data, manager, routing, solution, vehicles, orders, delivery, store
            )

            try:
                strategy_enum = routing_enums_pb2.FirstSolutionStrategy
                variant["strategy"] = strategy_enum.keys()[strategies[i]]  
            except (IndexError, AttributeError):
                variant["strategy"] =  ({strategies[i]})

            variants.append(variant)



    if not variants:
        raise ValueError("ERROR: No valid route variants generated.")

    return variants


def assign_vehicles_and_extract_routes(
    data, manager, routing, solution, vehicles, orders, delivery, store
):
    routes = []
    total_distance = 0

    for vehicle_id in range(data["num_vehicles"]):
        index = routing.Start(vehicle_id)
        route, route_distance = [], 0
        vehicle_weight = 0

        while not routing.IsEnd(index):
            route.append(manager.IndexToNode(index))
            prev_idx = index
            index = solution.Value(routing.NextVar(index))
            route_distance += data["distance_matrix"][manager.IndexToNode(prev_idx)][
                manager.IndexToNode(index)
            ]

        route.append(manager.IndexToNode(index))
        assigned_order_ids = [orders[i - 1].id for i in route[1:-1]]

        mapped_route = [
            (
                {
                    "location": "Warehouse",
                    "coordinates": [store.location.point.y, store.location.point.x],
                }
                if i == 0
                else {
                    "location": orders[i - 1].order_id,
                    "coordinates": [
                        orders[i - 1].delivery_location.point.y,
                        orders[i - 1].delivery_location.point.x,
                    ],
                }
            )
            for i in route
        ]

        for order_id in assigned_order_ids:
            order = Order.objects.get(id=order_id)
            vehicle_weight += order.weight

        vehicle_route_info = {
            "vehicle_no": vehicles[vehicle_id].vehicle_no,
            "average_speed_kmh": vehicles[vehicle_id].average_speed,
            "capacity": vehicles[vehicle_id].capacity,
            "assigned_order_weight": vehicle_weight,
            "remaining_capacity": vehicles[vehicle_id].capacity - vehicle_weight,
            "route_distance_km": route_distance / 1000,
            "route": mapped_route,
        }

        for order_id in assigned_order_ids:
            order = Order.objects.get(id=order_id)
            order.vehicle = vehicles[vehicle_id]
            order.delivery = delivery
            order.save()

        routes.append(vehicle_route_info)
        total_distance += route_distance

    return {"vehicle_routes": routes, "total_distance": total_distance / 1000}
