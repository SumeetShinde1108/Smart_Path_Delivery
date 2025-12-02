from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from delivery_app.models import Delivery, Order, Store, Vehicle


class Command(BaseCommand):
    help = "Create deliveries from existing orders (grouped by date) and assign available vehicles."

    def handle(self, *args, **options):
        store = Store.objects.first()
        if not store:
            self.stderr.write("No store available. Please add a store before assigning vehicles.")
            return

        available_vehicles = list(Vehicle.objects.all())
        if not available_vehicles:
            self.stderr.write("No vehicles available. Please add vehicles before assignment.")
            return

        orders = Order.objects.all().order_by("date_of_order")
        deliveries = Delivery.objects.all().select_related("store")

        if not orders.exists() and not deliveries.exists():
            self.stdout.write("No orders or deliveries available for assignment.")
            return

        deliveries_created = 0
        deliveries_updated = 0
        vehicles_assigned = 0

        orders_by_date: dict = defaultdict(list)
        for order in orders:
            orders_by_date[order.date_of_order].append(order)

        with transaction.atomic():
            for delivery_date, orders_for_date in orders_by_date.items():
                delivery, created = Delivery.objects.get_or_create(
                    store=store,
                    date_of_delivery=delivery_date,
                    defaults={"total_weight": 0},
                )

                if created:
                    deliveries_created += 1

                delivery.orders.add(*orders_for_date)
                delivery.total_weight = sum(order.weight for order in delivery.orders.all())
                delivery.save()

        deliveries = Delivery.objects.all().select_related("store")

        with transaction.atomic():
            for delivery in deliveries:
                previous_vehicle_ids = set(
                    delivery.vehicles.values_list("id", flat=True)
                )
                new_vehicle_ids = {vehicle.id for vehicle in available_vehicles}

                if previous_vehicle_ids != new_vehicle_ids:
                    deliveries_updated += 1
                    vehicles_assigned += 1

                delivery.vehicles.set(available_vehicles)
                delivery.total_weight = sum(order.weight for order in delivery.orders.all())
                delivery.save()

        parts = []
        if deliveries_created:
            parts.append(f"{deliveries_created} new delivery{'ies' if deliveries_created != 1 else ''} created")
        if deliveries_updated:
            parts.append(f"{deliveries_updated} existing delivery{'ies' if deliveries_updated != 1 else ''} updated")
        if vehicles_assigned:
            parts.append(f"vehicles assigned to {vehicles_assigned} delivery{'ies' if vehicles_assigned != 1 else ''}")

        if parts:
            self.stdout.write(
                "; ".join(parts)
            )
        else:
            self.stdout.write("All deliveries already have vehicles assigned.")
