from django.contrib.gis.db import models


class Location(models.Model):
    '''
    Represents a location with an address and geographical coordinates.
    '''
    address = models.CharField(max_length=255)
    point = models.PointField()
    
    class Meta:
        verbose_name = "Location"
        verbose_name_plural = "01 Locations"

    def __str__(self):
        return f'Address :{self.address}'


class Order(models.Model):
    '''
    Stores customer order details, including weight, location, and date.
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


class Distance(models.Model):
    '''
    Tracks the distance between two locations. 
    '''
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
    distance = models.FloatField(help_text="Distance between two locations")

    class Meta:
        verbose_name = "Distance"
        verbose_name_plural = "03 Distances"
        unique_together = ("location_a", "location_b")
        
    def __str__(self):
        return f"{self.location_a.address} to {self.location_b.address}: {self.distance} km"


class Vehicle(models.Model):
    '''
    Represents a vehicle with its capacity, speed, and availability.
    '''
    vehicle_no = models.CharField(max_length=64, unique=True)
    vehicle_capacity = models.FloatField(help_text="Weight capacity in kilograms")
    average_speed = models.FloatField(help_text="Average speed in km/h")
    is_available = models.BooleanField(
        default=True, 
        help_text='Avaibility of a vehicle',
    )

    class Meta:
        verbose_name = "Vehicle"
        verbose_name_plural = "04 Vehicles"
        ordering = ['average_speed']

    def __str__(self):
        return f"Vehicle {self.vehicle_no} - Capacity: {self.vehicle_capacity} kg"


class Route(models.Model):
    '''
    Represent detail optimized routes for delivering orders using vehicles.
    '''
    vehicles = models.ManyToManyField(Vehicle, blank=True)
    order = models.ForeignKey(
        Order, 
        on_delete=models.CASCADE,
        related_name="Order_Route"
    )
    total_distance = models.FloatField(help_text="Total distance covered by a single route in kms")
    total_weight = models.FloatField(
        default=0,
        help_text="Total weight of all orders assigned to this route in kgs",
    )
    path = models.JSONField(default=list)

    class Meta:
        verbose_name = "Route"
        verbose_name_plural = "05 Routes"
        ordering = ['-total_distance']

    def __str__(self):
        return f"Route {self.id} - {self.total_distance} km"


class Delivery(models.Model):
    '''
    Plans and tracks deliveries for a specific date.
    '''
    route = models.ForeignKey(
        Route, 
        on_delete=models.CASCADE,
        related_name="Route_Delivery"
    )
    total_vehicles = models.IntegerField(help_text="No of vehicles allocated for this delivery")
    total_distance = models.FloatField(help_text="Total distance covered by all routes in kms")
    total_weight = models.FloatField(
        help_text="Combined weight of all orders assigned to this delivery, in kilograms",
    )
    date_of_delivery = models.DateField()
    
    class Meta:
        verbose_name = "Delivery"
        verbose_name_plural = "06 Deliveries"
        ordering = ['-date_of_delivery']

    def __str__(self):
        return f"Delivery date {self.date_of_delivery} - {self.total_vehicles} vehicles"

    