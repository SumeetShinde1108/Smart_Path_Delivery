from datetime import date
from django.db import models


class Vehicle(models.Model):
    name = models.CharField(max_length=64)
    max_weight_capacity = models.FloatField()

    class Meta:
        verbose_name = "Vehicle"
        verbose_name_plural = "Vehicles"

    def __str__(self):
        return self.name


class Location(models.Model):
    name = models.CharField(max_length=64)
    longitude = models.FloatField()
    latitude = models.FloatField()

    class Meta:
        verbose_name = "Location"
        verbose_name_plural = "Locations"

    def __str__(self):
        return self.name


class Order(models.Model):
    STATUS_PENDING = 'Pending'
    STATUS_PARTIAL_DELIVERY = 'Partially_Delivered'
    STATUS_COMPLETED = 'Completed' 

    CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PARTIAL_DELIVERY, "Partially_Delivered"),
        (STATUS_COMPLETED, "Complete")
    ]

    location = models.ForeignKey(
        Location, 
        on_delete=models.CASCADE,
        related_name="Orders"
        )
    name = models.CharField(max_length=64)
    total_weight = models.FloatField() 
    status = models.CharField(
        max_length=64,
        choices=CHOICES,
        default="Pending"
        )

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"

    def __str__(self):
        return self.name 


class Delivery(models.Model):
    assigned_vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="Deliveries"
        )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="Deliveries" 
        ) 
    delivery_date = models.DateField
    delivered_weight = models.FloatField()
    sequence = models.PositiveIntegerField()
    
    class Meta:
        verbose_name = "Delivery"
        verbose_name_plural = "Deliveries"

    def __str__(self):
        return (
            f"Vehicle: {self.assigned_vehicle.name}, "
            f"Order: {self.order.name}, "
            f"Weight: {self.delivered_weight} kg, "
            f"Sequence: {self.sequence}"
        )



