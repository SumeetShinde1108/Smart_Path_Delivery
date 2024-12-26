from django.db import models
from delivery_app.utils import calculate_distance 


class Location(models.Model):
    address = models.CharField(max_length=64)
    latitude = models.FloatField()
    longitude = models.FloatField()

    class Meta:
        verbose_name = "Location"
        verbose_name_plural = "Locations"

    def __str__(self):
        return self.address


class Order(models.Model):
    order_id = models.CharField(max_length=64, unique=True)
    weight = models.FloatField(help_text="Weight in kilograms")
    delivery_location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE
    )
    date_of_order = models.DateField()

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"

    def __str__(self):
        return f"Order {self.order_id} - {self.weight} kg"


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
    distance = models.FloatField(null=True, blank=True)

    class Meta:
        unique_together = ("location_a", "location_b")
        verbose_name = "Distance"
        verbose_name_plural = "Distances"
        
    def __str__(self):
        return f"{self.location_a.address} to {self.location_b.address}: {self.distance} km"

    def save(self, *args, **kwargs):
        if self.location_a == self.location_b:
            raise ValueError("Locations A and B cannot be the same.")

        if self.distance is None:
            self.distance = calculate_distance(
                self.location_a.latitude,
                self.location_a.longitude,
                self.location_b.latitude,
                self.location_b.longitude,
         )   

        super().save(*args, **kwargs)


    @classmethod
    def get_distance(cls, loc_a, loc_b):
        try:
            return cls.objects.get(location_a=loc_a, location_b=loc_b).distance
        except cls.DoesNotExist:
            try:
                return cls.objects.get(location_a=loc_b, location_b=loc_a).distance
            except cls.DoesNotExist:
                raise ValueError("Distance between locations not defined.")


class Vehicle(models.Model):
    vehicle_no = models.CharField(max_length=50, unique=True)
    vehicle_capacity = models.FloatField(help_text="Weight capacity in kilograms")
    average_speed = models.FloatField(help_text="Average speed in km/h")
    is_available = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Vehicle"
        verbose_name_plural = "Vehicles"

    def __str__(self):
        return f"Vehicle {self.vehicle_no} - Capacity: {self.vehicle_capacity} kg"


class Route(models.Model):
    vehicles = models.ManyToManyField(Vehicle, blank=True)
    order = models.ForeignKey(
        Order, 
        on_delete=models.CASCADE
    )
    total_distance = models.FloatField(help_text="Total distance covered by a single route in kms")
    total_weight = models.FloatField(
        help_text="Total weight of all orders assigned to this route in kgs",
        default=0
    )
    path = models.JSONField(default=list)

    class Meta:
        verbose_name = "Route"
        verbose_name_plural = "Routes"

    def __str__(self):
        return f"Route {self.id} - {self.total_distance} km"


class Delivery(models.Model):
    route = models.ForeignKey(
        Route, 
        on_delete=models.CASCADE
    )
    total_vehicles = models.IntegerField(help_text="No of vehicles allocated for this delivery")
    total_distance = models.FloatField(help_text="Total distance covered by all routes in kms")
    total_weight = models.FloatField(
        help_text="Combined weight of all orders assigned to this delivery, in kilograms",
        default=0
    )
    date_of_delivery = models.DateField()

    class Meta:
        verbose_name = "Delivery Planning"
        verbose_name_plural = "Delivery Plannings"

    def __str__(self):
        return f"Delivery Plan {self.date_of_delivery} - {self.total_vehicles} vehicles"

    