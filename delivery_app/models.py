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
        verbose_name = 'Location'
        verbose_name_plural = 'Locations'

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


    



