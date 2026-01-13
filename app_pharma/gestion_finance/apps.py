from django.apps import AppConfig


class GestionFinanceConfig(AppConfig):
    name = 'gestion_finance'
    verbose_name = 'gestion des finances'
    
    
    def ready(self):
        import gestion_finance.signals
