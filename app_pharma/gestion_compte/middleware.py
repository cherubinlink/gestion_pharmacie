from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta


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


class AutoLogoutMiddleware:
    '''Déconnecte automatiquement après 30 min d'inactivité'''
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated:
            last_activity = request.session.get('last_activity')
            
            if last_activity:
                last_activity = timezone.datetime.fromisoformat(last_activity)
                
                # Si inactif depuis 30 minutes
                if timezone.now() - last_activity > timedelta(minutes=30):
                    from django.contrib.auth import logout
                    logout(request)
                    return redirect('gestion_compte:connexion')
            
            # Mettre à jour dernière activité
            request.session['last_activity'] = timezone.now().isoformat()
        
        return self.get_response(request)
