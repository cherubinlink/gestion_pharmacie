from django.apps import AppConfig


class GestionSuivitConfig(AppConfig):
    name = 'gestion_suivit'
    verbose_name = 'gestion des suivits'
    
    
    def ready(self):
        import gestion_suivit.signals
