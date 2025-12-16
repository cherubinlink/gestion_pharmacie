from django.apps import AppConfig


class GestionCompteConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gestion_compte'
    verbose_name = 'Gestion des Comptes'

    def ready(self):
        import gestion_compte.signals
