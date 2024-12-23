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

