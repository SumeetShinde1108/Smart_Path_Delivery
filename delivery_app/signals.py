from django.db.models.signals import post_save
from django.dispatch import receiver
from delivery_app.models import Order, Store, Delivery


@receiver(post_save, sender=Order)
def create_or_update_delivery(sender, instance, created, **kwargs):
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
    delivery.save()
