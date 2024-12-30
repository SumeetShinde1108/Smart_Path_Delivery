from django.contrib import admin
from delivery_app.models import (
    Location,
    Order,
    Store,
    Vehicle,
    Delivery
)


class OrderInline(admin.TabularInline):
    model = Order
    extra = 1


class StoreInline(admin.TabularInline):
    model = Store
    extra = 1

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('address', 'point')
    search_fields = ('address',)
    ordering = ('address',)
    Inlines = [OrderInline, StoreInline]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'weight', 'delivery_location', 'date_of_order')
    list_filter = ('date_of_order',)
    search_fields = ('order_id', 'delivery_location__address')
    ordering = ('-date_of_order',)


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ('name', 'location')
    search_fields = ('name', 'location__address')
    ordering = ('name',)


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('vehicle_no', 'capacity', 'average_speed')
    list_filter = ('average_speed',)
    search_fields = ('vehicle_no',)
    ordering = ('average_speed',)


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ('store', 'date_of_delivery', 'total_weight', 'vehicle')
    list_filter = ('date_of_delivery',)
    search_fields = ('store__name', 'store__location__address')
    ordering = ('-date_of_delivery',)


    def vehicle(self, obj):
        return obj.vehicles.all()
    vehicle.short_description = 'Vehicles'

