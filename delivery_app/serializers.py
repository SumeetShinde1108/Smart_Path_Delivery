from rest_framework import serializers
from delivery_app.models import Location, Order, Store, Vehicle, Delivery


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ["id", "address", "point"]


class OrderSerializer(serializers.ModelSerializer):
    delivery_location = LocationSerializer()

    class Meta:
        model = Order
        fields = ["id", "order_id", "weight", "delivery_location", "date_of_order"]

    def create(self, validated_data):
        location_data = validated_data.pop("delivery_location")
        location = Location.objects.create(**location_data)
        order = Order.objects.create(delivery_location=location, **validated_data)
        return order

    def update(self, instance, validated_data):
        location_data = validated_data.pop("delivery_location", None)
        if location_data:
            for attr, value in location_data.items():
                setattr(instance.delivery_location, attr, value)
            instance.delivery_location.save()
        return super().update(instance, validated_data)


class StoreSerializer(serializers.ModelSerializer):
    location = LocationSerializer()

    class Meta:
        model = Store
        fields = ["name", "location"]
