from django.apps import AppConfig

class DeliveryAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "delivery_app"

    def ready(self):
        import delivery_app.signals
