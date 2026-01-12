from django.apps import AppConfig


class GestionStockConfig(AppConfig):
    name = 'gestion_stock'
    verbose_name = 'gestions de stock'
    
    
    def ready(self):
        import gestion_stock.signals
