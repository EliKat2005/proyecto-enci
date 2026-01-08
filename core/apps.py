from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        # Import signal handlers to keep UserProfile.role in sync with Groups
        try:
            import core.signals  # noqa: F401
        except Exception:
            # Avoid breaking startup if signals fail to import during migrations
            pass
