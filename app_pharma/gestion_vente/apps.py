from django.apps import AppConfig


class GestionVenteConfig(AppConfig):
    name = 'gestion_vente'
    verbose_name = 'gestions des ventes'
    
    
    def ready(self):
        import gestion_vente.signals
