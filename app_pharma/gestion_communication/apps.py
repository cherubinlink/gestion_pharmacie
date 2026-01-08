from django.apps import AppConfig


class GestionCommunicationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gestion_communication'
    verbose_name = 'gestion des communications'
    
    
    
    def ready(self):
        import gestion_communication.signals
