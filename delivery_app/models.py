from django.contrib.gis.db import models


class Location(models.Model):
    """
    Represents a physical location with an address and coordinates for deliveries.
    """

    address = models.CharField(max_length=255)
    point = models.PointField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Location"
        verbose_name_plural = "01 Locations"

    def __str__(self):
        return f"Address: {self.address}"


class Order(models.Model):
    """
    Captures order details, including weight, delivery location, and order date.
    """

    order_id = models.CharField(max_length=64, unique=True)
    weight = models.FloatField(help_text="Weight in kilograms")
    delivery_location = models.ForeignKey(
        Location, on_delete=models.CASCADE, related_name="Location_Order"
    )
    date_of_order = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "02 Orders"
        ordering = ["-date_of_order"]

    def __str__(self):
        return f"Order {self.order_id} - {self.weight} kg"


class Store(models.Model):
    """
    Represents stores where all items are dispatched for delivery.
    """

    name = models.CharField(max_length=128)
    location = models.ForeignKey(
        Location, on_delete=models.CASCADE, related_name="Location_Store"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Store"
        verbose_name_plural = "03 Stores"

    def __str__(self):
        return f"Store name: {self.name}, location: {self.location}"


class Vehicle(models.Model):
    """
    Represents delivery vehicles with capacity, speed, and availability status.
    """

    vehicle_no = models.CharField(max_length=64, unique=True)
    capacity = models.FloatField(help_text="Weight capacity in kilograms")
    average_speed = models.FloatField(help_text="Average speed in km/h")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Vehicle"
        verbose_name_plural = "04 Vehicles"
        ordering = ["-average_speed"]

    def clean(self):
        if self.capacity <= 0:
            raise ValidationError("Vehicle capacity must be greater than zero.")
        if self.average_speed <= 0:
            raise ValidationError("Vehicle average speed must be greater than zero.")

    def __str__(self):
        return f"Vehicle {self.vehicle_no} - Capacity: {self.capacity} kg"


class Delivery(models.Model):
    """
    Tracks delivery details for a single day, with assigned store, vehicles, and total weight.
    """

    store = models.ForeignKey(
        Store, on_delete=models.CASCADE, related_name="deliveries"
    )
    orders = models.ManyToManyField(
        Order, related_name="deliveries", help_text="Orders included in this delivery"
    )
    vehicles = models.ManyToManyField(
        Vehicle,
        related_name="deliveries",
        help_text="Vehicles allocated for this delivery",
    )
    total_weight = models.FloatField(
        help_text="Combined weight of all orders for this delivery in kilograms"
    )
    date_of_delivery = models.DateField(
        unique=True, help_text="Delivery date (only one delivery per day)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Delivery"
        verbose_name_plural = "05 Deliveries"
        ordering = ["-date_of_delivery"]

    def clean(self):
        if not self.vehicles.exists():
            raise ValidationError(
                "At least one vehicle must be assigned to the delivery."
            )
        if self.total_weight <= 0:
            raise ValidationError(
                "The total weight of the delivery must be greater than zero."
            )

    def save(self, *args, **kwargs):
        if not self.pk:  
            vehicles = Vehicle.objects.all()
            if not vehicles.exists():
                raise ValidationError("No vehicles available for assignment.")

            total_capacity = sum(vehicle.capacity for vehicle in vehicles)
            if total_capacity < self.total_weight:
                raise ValidationError(
                )

            super().save(*args, **kwargs)  
            self.vehicles.set(vehicles)  
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"Delivery {self.date_of_delivery} - {self.total_weight} kg"
