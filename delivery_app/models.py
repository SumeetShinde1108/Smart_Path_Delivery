from django.contrib.gis.db import models


class Location(models.Model):
    '''
    Represents a physical location with an address and coordinates for deliveries.
    '''
    address = models.CharField(max_length=255)
    point = models.PointField()

    class Meta:
        verbose_name = "Location"
        verbose_name_plural = "01 Locations"

    def __str__(self):
        return f'Address: {self.address}'


class Order(models.Model):
    '''
    Captures order details, including weight, delivery location, and order date.
    '''
    order_id = models.CharField(max_length=64, unique=True)
    weight = models.FloatField(help_text="Weight in kilograms")
    delivery_location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name="Location_Order"
    )
    date_of_order = models.DateField()

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "02 Orders"
        ordering = ['-date_of_order']

    def __str__(self):
        return f"Order {self.order_id} - {self.weight} kg"


class Store(models.Model):
    '''
    Represents stores where all items are dispatched for delivery.
    '''
    name = models.CharField(max_length=128)
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name="Location_Store"
    )

    class Meta:
        verbose_name = "Store"
        verbose_name_plural = "03 Stores"

    def __str__(self):
        return f'Store name: {self.name}, location: {self.location}'


class Vehicle(models.Model):
    '''
    Represents delivery vehicles with capacity, speed, and availability status.
    '''
    vehicle_no = models.CharField(max_length=64, unique=True)
    capacity = models.FloatField(help_text="Weight capacity in kilograms")
    average_speed = models.FloatField(help_text="Average speed in km/h")

    class Meta:
        verbose_name = "Vehicle"
        verbose_name_plural = "04 Vehicles"
        ordering = ['average_speed']

    def __str__(self):
        return f"Vehicle {self.vehicle_no} - Capacity: {self.capacity} kg"


class Delivery(models.Model):
    '''
    Tracks delivery details for a single day, with assigned store, vehicles, and total weight.
    '''
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="deliveries"
    )
    vehicles = models.ManyToManyField(
        Vehicle,
        related_name="deliveries",
        help_text="Vehicles allocated for this delivery"
    )
    total_weight = models.FloatField(
        help_text="Combined weight of all orders for this delivery in kilograms"
    )
    date_of_delivery = models.DateField(
        unique=True, help_text="Delivery date (only one delivery per day)"
    )

    class Meta:
        verbose_name = "Delivery"
        verbose_name_plural = "05 Deliveries"
        ordering = ['-date_of_delivery']

    def __str__(self):
        return f"Delivery {self.date_of_delivery} - {self.total_weight} kg"

