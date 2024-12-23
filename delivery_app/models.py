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
        return f"{self.location_a.address} ↔ {self.location_b.address}: {self.distance} km"

    def calculate_distance(self):
        lat1 = radians(self.location_a.latitude)
        lon1 = radians(self.location_a.longitude)
        lat2 = radians(self.location_b.latitude)
        lon2 = radians(self.location_b.longitude)

        dlon = lon2 - lon1
        dlat = lat2 - lat1

        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        R = 6371
        return round(R * c, 2)

    @classmethod
    def get_distance(cls, loc_a, loc_b):
        try:
            return cls.objects.get(location_a=loc_a, location_b=loc_b).distance_km
        except cls.DoesNotExist:
            return cls.objects.get(location_a=loc_b, location_b=loc_a).distance_km
        except cls.DoesNotExist:
            raise ValueError("Distance between locations not defined.")
    
    def save(self, *args, **kwargs):
        if not self.distance:
            self.distance = self.calculate_distance()
        super().save(*args, **kwargs)












