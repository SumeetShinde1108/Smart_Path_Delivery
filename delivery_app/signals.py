from django.db import transaction
from django.dispatch import receiver
from django.db.models.signals import post_save
from delivery_app.models import Order, Store, Vehicle, Delivery


@receiver(post_save, sender=Order)
def create_or_update_delivery(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        store = Store.objects.first()
        if not store:
            raise ValueError("No store is defined in the system.")

        delivery, created = Delivery.objects.get_or_create(
            store=store,
            date_of_delivery=instance.date_of_order,
            defaults={"total_weight": 0},
        )

        delivery.orders.add(instance)
        delivery.total_weight += instance.weight

        if not delivery.vehicles.exists():
            available_vehicles = Vehicle.objects.all()
            if available_vehicles.exists():
                delivery.vehicles.set(available_vehicles)

        delivery.save()

    except ValueError as ve:
        print(f"Error: {ve}")
        raise
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise
