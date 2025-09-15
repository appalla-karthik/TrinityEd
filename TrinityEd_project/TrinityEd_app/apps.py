from django.apps import AppConfig

class TrinityEdAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'TrinityEd_app'

    def ready(self):
        import TrinityEd_app.signals  # ✅ bas signals yaha load karni hai
