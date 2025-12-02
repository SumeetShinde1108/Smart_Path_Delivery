from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DeliveryDetailAPIView,
    DeliveryListByDateView,
    LocationViewSet,
    OrderViewSet,
    StoreViewSet,
    VehicleViewSet,
    add_location,
    add_location_and_order,
    add_order,
    add_store,
    add_vehicle,
    add_vehicle_data,
    assign_vehicles_to_delivery,
    home,
    optimization_visualizations,
)

router = DefaultRouter()
router.register(r"locations", LocationViewSet)
router.register(r"orders", OrderViewSet)
router.register(r"stores", StoreViewSet)
router.register(r"vehicles", VehicleViewSet)

urlpatterns = [
    path("", home, name="home"),
    path("add-order/", add_order, name="add-order"),
    path("add-store/", add_store, name="add-store"),
    path("add-vehicle/", add_vehicle, name="add-vehicle"),
    path("add_location/", add_location, name="add-location"),
    path("add_location_and_order/", add_location_and_order, name="add-location-and-order"),
    path("assign-vehicles/", assign_vehicles_to_delivery, name="assign-vehicles"),
    path("visuals/<int:delivery_id>/", optimization_visualizations, name="visuals"),
    path("delivery/<int:pk>/", DeliveryDetailAPIView.as_view(), name="delivery-detail"),
    path("delivery/by-date/", DeliveryListByDateView.as_view(), name="delivery-by-date"),
    path("api/add_vehicle/", add_vehicle_data, name="api-add-vehicle"),
    path("api/", include(router.urls)),
]
