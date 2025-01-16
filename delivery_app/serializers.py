from rest_framework import serializers
from delivery_app.models import Location, Order, Store, Vehicle, Delivery


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ["id", "address", "point"]
