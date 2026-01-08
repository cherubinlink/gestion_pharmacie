from django.apps import AppConfig


class GestionRhConfig(AppConfig):
    name = 'gestion_rh'
    verbose_name = 'gestions resouses humaines'
    
    
    def ready(self):
        import gestion_rh.signals
