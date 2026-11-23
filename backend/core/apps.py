from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        from django.db.models.signals import pre_save

        from core.date_order import enforce_date_order
        from core.numeric_bounds import enforce_numeric_bounds

        pre_save.connect(enforce_numeric_bounds, dispatch_uid="core.numeric_bounds")
        pre_save.connect(enforce_date_order, dispatch_uid="core.date_order")
