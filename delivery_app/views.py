import json
import logging
import requests
from datetime import datetime
from django.views import View
from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.db import IntegrityError
from rest_framework.views import APIView
from django.contrib.gis.geos import Point
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.core.management import call_command
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from delivery_app.utils import assign_routes_to_delivery
from delivery_app.signals import create_or_update_delivery
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from delivery_app.models import Location, Order, Store, Vehicle, Delivery
from delivery_app.serializers import (
    LocationSerializer,
    OrderSerializer,
    StoreSerializer,
    VehicleSerializer,
    DeliverySerializer,
)

logger = logging.getLogger(__name__)


def home(request):
    available_dates = Delivery.objects.values("date_of_delivery").distinct()
    context = {
        "locations": Location.objects.all(),
        "orders": Order.objects.all(),
        "stores": Store.objects.all(),
        "vehicles": Vehicle.objects.all(),
        "deliveries": Delivery.objects.all(),
        "available_dates": [date["date_of_delivery"] for date in available_dates],
    }
    return render(request, "home.html", context)


def add_order(request):
    return render(request, "add_order.html")


def add_store(request):
    return render(request, "add_store.html")


@csrf_exempt
def add_location(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            store_name = data.get("store_name")
            address = data.get("address")
            latitude = data.get("latitude")
            longitude = data.get("longitude")

            if not all([store_name, address, latitude, longitude]):
                return JsonResponse({"error": "Missing required fields"}, status=400)

            location = Location.objects.create(
                address=address, point=f"POINT({longitude} {latitude})"
            )

            store = Store.objects.create(name=store_name, location=location)

            return JsonResponse(
                {"message": f"Store '{store_name}' added successfully!"}, status=201
            )

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)


def add_vehicle(request):
    return render(request, "add_vehicle.html")


def assign_vehicles_to_delivery(request):
    try:
        call_command("vehicles_for_delivery")
        messages.success(
            request, "Vehicles have been successfully assigned to the delivery."
        )
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
    return redirect("home")


@csrf_exempt
def add_location_and_order(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            order_id = data.get("order_id")
            weight = data.get("weight")
            date_of_order = data.get("date_of_order")
            address = data.get("address")
            latitude = data.get("latitude")
            longitude = data.get("longitude")

            if not all([order_id, weight, date_of_order, address, latitude, longitude]):
                return JsonResponse({"error": "Missing required fields"}, status=400)

            latitude = float(latitude)
            longitude = float(longitude)

            location = Location.objects.create(
                address=address, point=f"POINT({longitude} {latitude})"
            )

            order = Order.objects.create(
                order_id=order_id,
                weight=float(weight),
                date_of_order=date_of_order,
                delivery_location=location,
            )

            return JsonResponse({"message": "Order added successfully!"}, status=201)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)


class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def create(self, request, *args, **kwargs):
        location_data = request.data.pop("delivery_location", None)
        if location_data:
            location_serializer = LocationSerializer(data=location_data)
            if location_serializer.is_valid():
                location = location_serializer.save()
                request.data["delivery_location"] = location.id
        return super().create(request, *args, **kwargs)


class StoreViewSet(viewsets.ModelViewSet):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer

    def create(self, request, *args, **kwargs):
        location_data = request.data.pop("location", None)
        if location_data:
            location_serializer = LocationSerializer(data=location_data)
            if location_serializer.is_valid():
                location = location_serializer.save()
                request.data["location"] = location.id
        return super().create(request, *args, **kwargs)


class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer


class DeliveryDetailAPIView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            delivery_id = kwargs.get("pk")
            delivery = Delivery.objects.prefetch_related("orders", "vehicles").get(
                id=delivery_id
            )

            store = delivery.store
            orders = list(delivery.orders.all())
            vehicles = list(delivery.vehicles.all())

            logging.debug(f"Store: {store}, Orders: {orders}, Vehicles: {vehicles}")

            solution = assign_routes_to_delivery(
                store, orders, vehicles, delivery.date_of_delivery
            )
            return Response(solution, status=status.HTTP_200_OK)
        except Delivery.DoesNotExist:
            return Response(
                {"error": "Delivery not found"}, status=status.HTTP_404_NOT_FOUND
            )


def optimization_visualizations(request, delivery_id):
    delivery = get_object_or_404(Delivery, id=delivery_id)
    api_url = f"{settings.SITE_URL}/delivery/{delivery_id}/"

    try:
        response = requests.get(api_url)
        response.raise_for_status()
        optimization_data = response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch optimization data: {e}")
        return render(
            request, "error.html", {"message": "Unable to fetch optimization data."}
        )

    solution1_routes = optimization_data[0].get("vehicle_routes", [])
    solution2_routes = optimization_data[1].get("vehicle_routes", [])
    solution3_routes = optimization_data[2].get("vehicle_routes", [])

    def process_routes(routes):
        processed_routes = []
        for route in routes:
            try:
                vehicle_no = route.get("vehicle_no", "Unknown Vehicle")
                route_distance_km = route.get("route_distance_km", float("inf"))
                assigned_order_weight = route.get("assigned_order_weight", 0)
                average_speed_kmh = route.get("average_speed_kmh", 0)
                remaining_capacity = route.get("remaining_capacity", 0)
                capacity = route.get("capacity", 0)
                coordinates = [
                    [coord["coordinates"][0], coord["coordinates"][1]]
                    for coord in route.get("route", [])
                    if coord.get("coordinates")
                ]

                processed_routes.append(
                    {
                        "vehicle_no": vehicle_no,
                        "route_distance_km": route_distance_km,
                        "assigned_order_weight": assigned_order_weight,
                        "average_speed_kmh": average_speed_kmh,
                        "remaining_capacity": remaining_capacity,
                        "capacity": capacity,
                        "coordinates": coordinates,
                    }
                )

            except Exception as e:
                logger.warning(f"Error processing route data: {route}. Error: {e}")
        return processed_routes

    solution1 = process_routes(solution1_routes)
    solution2 = process_routes(solution2_routes)
    solution3 = process_routes(solution3_routes)

    def total_distance(routes):
        return sum(route["route_distance_km"] for route in routes)

    total_distance_solution1 = total_distance(solution1)
    total_distance_solution2 = total_distance(solution2)
    total_distance_solution3 = total_distance(solution3)

    best_solution = min(
        [
            (solution1, total_distance_solution1),
            (solution2, total_distance_solution2),
            (solution3, total_distance_solution3),
        ],
        key=lambda x: x[1],
    )[0]

    context = {
        "delivery": delivery,
        "solution1": json.dumps(solution1),
        "solution2": json.dumps(solution2),
        "solution3": json.dumps(solution3),
        "best_solution": json.dumps(best_solution),
    }

    print("solution 1:", solution1)
    print("solution 2:", solution2)
    print("solution 3:", solution3)
    print("best solution:", best_solution)

    return render(request, "visualization.html", context)


class DeliveryListByDateView(View):
    def get(self, request, *args, **kwargs):
        delivery_date = request.GET.get("delivery_date")

        try:
            delivery_date = datetime.strptime(delivery_date, "%Y-%m-%d").date()
        except ValueError:
            return render(request, "error.html", {"message": "Invalid date format."})

        deliveries = Delivery.objects.filter(
            date_of_delivery=delivery_date
        ).prefetch_related("orders", "vehicles")

        if not deliveries:
            return render(
                request,
                "error.html",
                {"message": "No deliveries found for the given date."},
            )

        return render(
            request,
            "delivery_list_by_date.html",
            {"deliveries": deliveries, "delivery_date": delivery_date},
        )


@csrf_protect
def add_vehicle_data(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON payload."}, status=400)

        vehicle_no = data.get("vehicle_no")
        capacity = data.get("capacity")
        average_speed = data.get("average_speed")

        if not all([vehicle_no, capacity, average_speed]):
            return JsonResponse({"error": "All fields are required."}, status=400)

        try:
            vehicle = Vehicle.objects.create(
                vehicle_no=vehicle_no,
                capacity=capacity,
                average_speed=average_speed,
            )
            return JsonResponse({"message": "Vehicle added successfully!"}, status=201)
        except IntegrityError:
            return JsonResponse({"error": "Vehicle number must be unique."}, status=400)

    return JsonResponse({"error": "Invalid request method."}, status=405)
