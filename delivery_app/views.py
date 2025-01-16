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

