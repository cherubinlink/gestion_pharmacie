from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages


class PharmacieActiveMiddleware:
    """Middleware pour vérifier qu'une pharmacie est active"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # URLs exemptées de la vérification
        exemptions = [
            reverse('gestion_compte:connexion'),
            reverse('gestion_compte:inscription'),
            reverse('gestion_compte:deconnexion'),
            reverse('gestion_compte:configuration_pharmacie'),
        ]
        
        if request.user.is_authenticated and request.path not in exemptions:
            if not request.user.pharmacie_active and not request.path.startswith('/admin/'):
                messages.warning(
                    request,
                    'Veuillez configurer votre pharmacie pour continuer.'
                )
                return redirect('gestion_compte:configuration_pharmacie')
        
        response = self.get_response(request)
        return response