from django.apps import AppConfig


class EcommerceConfig(AppConfig):
    name = 'ecommerce'
    verbose_name = 'ecommerces'
    
    
    def ready(self):
        import ecommerce.signals
