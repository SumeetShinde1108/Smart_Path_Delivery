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

