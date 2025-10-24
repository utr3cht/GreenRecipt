from django.apps import AppConfig
from django.db import connection


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        if connection.vendor == "sqlite":
            with connection.cursor() as c:
                c.execute("PRAGMA journal_mode=WAL;")
                c.execute("PRAGMA synchronous=NORMAL;")
                c.execute("PRAGMA foreign_keys=ON;")
