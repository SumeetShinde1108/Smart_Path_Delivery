from django.db import models
from math import radians, sin, cos, sqrt, atan2


class Location(models.Model):
    address = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()

    class Meta:
        verbose_name='Location'
        verbose_name_plural='Locations'
    
    def __str__(self):
        return f"{self.address}"


class Order(models.Model):
    order_id = models.CharField(max_length=50, unique=True)
    weight_kg = models.FloatField(help_text="Weight in kgs")
    delivery_location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE
        )
    date_of_order = models.DateField()

    class Meta:
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
    
    def __str__(self):
        return f"Order {self.order_id} - {self.weight_kg} kg"

    @staticmethod
    def get_orders_for_date(delivery_date):
        return Order.objects.filter(date_of_order=delivery_date)


class Distance(models.Model):
    location_a = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name="distance_from"
        )
    location_b = models.ForeignKey(
        Location, 
        on_delete=models.CASCADE,
        related_name="distance_to"
        )
    distance = models.FloatField()

    class Meta:
        verbose_name = "Distance"
        verbose_name_plural = "Distances"

    def __str__(self):
        return f"{self.location_a.address} ↔ {self.location_b.address}: {self.distance_km} km"

        






