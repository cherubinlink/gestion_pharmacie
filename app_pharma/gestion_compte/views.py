from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from django.http import JsonResponse,HttpResponseForbidden
from django.contrib.auth.forms import PasswordChangeForm
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.db import transaction
from django.conf import settings
from django.db.models.functions import TruncDate
import logging
import re
import json
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from gestion_compte.models import (
    Utilisateur,UtilisateurManager,Pharmacie,ProfilUtilisateur,
    Role, PermissionSysteme, RolePermission, MembrePharmacie,
    HistoriqueConnexion, HistoriqueModificationPharmacie
)
from gestion_compte.forms import (
    InscriptionForm, ConnexionForm, ProfilUtilisateurForm, PharmacieForm,
    UtilisateurForm, InvitationMembreForm, PreferencesUtilisateurForm, 
) 
from django.core.paginator import Paginator

logger = logging.getLogger(__name__)

# Create your views here.


# ============================================================================
# VUE D'INSCRIPTION PRINCIPALE
# ============================================================================

@never_cache
@require_http_methods(["GET", "POST"])
def inscription_view(request):
    """
    Vue d'inscription complète avec validation et sécurité
    
    Fonctionnalités:
    - Validation des données
    - Vérification force mot de passe
    - Détection doublon email/username
    - Envoi email de bienvenue
    - Logging des inscriptions
    - Protection CSRF
    - Gestion erreurs
    """
    
    # Redirection si déjà connecté
    if request.user.is_authenticated:
        messages.info(request, 'Vous êtes déjà connecté.')
        return redirect('gestion_compte:dashboard')
    
    if request.method == 'POST':
        form = InscriptionForm(request.POST, request.FILES)
        
        if form.is_valid():
            try:
                # Création utilisateur avec transaction atomique
                with transaction.atomic():
                    # Créer l'utilisateur
                    user = form.save(commit=False)
                    
                    # Générer username si vide
                    if not user.username:
                        user.username = generer_username(
                            user.first_name, 
                            user.last_name, 
                            user.email
                        )
                    
                    # Définir statut initial
                    user.statut = 'actif'
                    user.is_active = True
                    
                    # Enregistrer IP de création
                    user.ip_derniere_connexion = obtenir_ip_client(request)
                    
                    # Sauvegarder
                    user.save()
                    
                    # Logger l'inscription
                    logger.info(
                        f"Nouvelle inscription: {user.email} "
                        f"(ID: {user.id}) depuis IP {user.ip_derniere_connexion}"
                    )
                    
                    # Envoyer email de bienvenue (asynchrone si possible)
                    try:
                        envoyer_email_bienvenue(user)
                    except Exception as e:
                        logger.error(f"Erreur envoi email bienvenue: {e}")
                        # Ne pas bloquer l'inscription si email échoue
                    
                    # Connexion automatique
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                    
                    # Mettre à jour dernière connexion
                    user.date_derniere_connexion = timezone.now()
                    user.save(update_fields=['date_derniere_connexion'])
                    
                    # Message de succès
                    messages.success(
                        request,
                        f'Bienvenue {user.get_full_name()} ! Votre compte a été créé avec succès.'
                    )
                    
                    # Redirection selon le type de compte
                    if user.is_superuser:
                        return redirect('admin:index')
                    else:
                        return redirect('gestion_compte:parametre_compte')
            
            except Exception as e:
                logger.error(f"Erreur lors de l'inscription: {e}", exc_info=True)
                messages.error(
                    request,
                    "Une erreur s'est produite lors de la création de votre compte. "
                    "Veuillez réessayer."
                )
        
        else:
            # Afficher les erreurs de validation
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, error)
                    else:
                        messages.error(request, f"{field}: {error}")
    
    else:
        form = InscriptionForm()
    
    # Statistiques pour la page (optionnel)
    stats = {
        'total_utilisateurs': Utilisateur.objects.filter(is_active=True).count(),
        'inscriptions_mois': Utilisateur.objects.filter(
            date_creation__month=timezone.now().month,
            date_creation__year=timezone.now().year
        ).count(),
    }
    
    context = {
        'form': form,
        'stats': stats,
        'page_title': 'Créer un compte',
        'show_captcha': getattr(settings, 'ENABLE_CAPTCHA', False),
    }
    
    return render(request, 'gestion_compte/inscription.html', context)


# ============================================================================
# VUE INSCRIPTION AJAX (Pour formulaires dynamiques)
# ============================================================================

@never_cache
@require_http_methods(["POST"])
def inscription_ajax_view(request):
    """
    Version AJAX de l'inscription pour les formulaires dynamiques
    Retourne JSON pour intégration frontend moderne
    """
    
    if request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Vous êtes déjà connecté.'
        }, status=400)
    
    try:
        form = InscriptionForm(request.POST, request.FILES)
        
        if form.is_valid():
            with transaction.atomic():
                user = form.save(commit=False)
                
                if not user.username:
                    user.username = generer_username(
                        user.first_name,
                        user.last_name,
                        user.email
                    )
                
                user.statut = 'actif'
                user.is_active = True
                user.ip_derniere_connexion = obtenir_ip_client(request)
                user.save()
                
                logger.info(f"Inscription AJAX: {user.email} (ID: {user.id})")
                
                # Envoyer email
                try:
                    envoyer_email_bienvenue(user)
                except Exception as e:
                    logger.error(f"Erreur email: {e}")
                
                # Connexion
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                user.date_derniere_connexion = timezone.now()
                user.save(update_fields=['date_derniere_connexion'])
                
                return JsonResponse({
                    'success': True,
                    'message': 'Compte créé avec succès !',
                    'user': {
                        'id': str(user.id),
                        'email': user.email,
                        'full_name': user.get_full_name(),
                        'username': user.username,
                    },
                    'redirect_url': '/compte/parametres/'
                })
        
        else:
            errors = {}
            for field, error_list in form.errors.items():
                errors[field] = [str(e) for e in error_list]
            
            return JsonResponse({
                'success': False,
                'errors': errors
            }, status=400)
    
    except Exception as e:
        logger.error(f"Erreur inscription AJAX: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Une erreur inattendue s\'est produite.'
        }, status=500)


# ============================================================================
# VÉRIFICATION DISPONIBILITÉ EMAIL/USERNAME
# ============================================================================

@never_cache
@require_http_methods(["GET"])
def verifier_email_disponible(request):
    """
    API pour vérifier si un email est disponible
    Utilisé pour validation en temps réel côté client
    """
    email = request.GET.get('email', '').strip().lower()
    
    if not email:
        return JsonResponse({
            'disponible': False,
            'message': 'Email requis'
        })
    
    # Validation format email
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        return JsonResponse({
            'disponible': False,
            'message': 'Format email invalide'
        })
    
    # Vérifier si existe
    existe = Utilisateur.objects.filter(email__iexact=email).exists()
    
    return JsonResponse({
        'disponible': not existe,
        'message': 'Email déjà utilisé' if existe else 'Email disponible',
        'email': email
    })


@never_cache
@require_http_methods(["GET"])
def verifier_username_disponible(request):
    """
    API pour vérifier si un username est disponible
    """
    username = request.GET.get('username', '').strip().lower()
    
    if not username:
        return JsonResponse({
            'disponible': False,
            'message': 'Username requis'
        })
    
    # Validation format username
    username_regex = r'^[a-zA-Z0-9_-]{3,30}$'
    if not re.match(username_regex, username):
        return JsonResponse({
            'disponible': False,
            'message': 'Username invalide (3-30 caractères alphanumériques)'
        })
    
    # Vérifier si existe
    existe = Utilisateur.objects.filter(username__iexact=username).exists()
    
    return JsonResponse({
        'disponible': not existe,
        'message': 'Username déjà utilisé' if existe else 'Username disponible',
        'username': username
    })


# ============================================================================
# ACTIVATION COMPTE PAR EMAIL
# ============================================================================

@never_cache
@require_http_methods(["GET"])
def activer_compte_view(request, token):
    """
    Activation du compte via lien email
    (Si vous implémentez la validation email)
    """
    try:
        # Décoder le token (utiliser JWT ou signing)
        from django.core.signing import Signer, BadSignature
        signer = Signer()
        
        try:
            user_id = signer.unsign(token)
        except BadSignature:
            messages.error(request, 'Lien d\'activation invalide ou expiré.')
            return redirect('gestion_compte:inscription')
        
        user = get_object_or_404(Utilisateur, id=user_id)
        
        if user.is_active:
            messages.info(request, 'Votre compte est déjà activé.')
            return redirect('gestion_compte:connexion')
        
        # Activer le compte
        user.is_active = True
        user.statut = 'actif'
        user.save()
        
        logger.info(f"Compte activé: {user.email} (ID: {user.id})")
        
        messages.success(
            request,
            'Votre compte a été activé avec succès ! Vous pouvez maintenant vous connecter.'
        )
        return redirect('gestion_compte:connexion')
    
    except Exception as e:
        logger.error(f"Erreur activation compte: {e}", exc_info=True)
        messages.error(request, 'Une erreur s\'est produite lors de l\'activation.')
        return redirect('gestion_compte:inscription')


# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def generer_username(first_name, last_name, email):
    """
    Génère un username unique basé sur le nom/email
    
    Exemple:
    - Jean Dupont → jean.dupont
    - Si existe → jean.dupont2, jean.dupont3, etc.
    """
    # Nettoyer et normaliser
    first = first_name.lower().strip()
    last = last_name.lower().strip()
    
    # Remplacer caractères spéciaux
    for char in [' ', 'é', 'è', 'ê', 'à', 'ù', 'ç']:
        replacements = {
            ' ': '.', 'é': 'e', 'è': 'e', 'ê': 'e',
            'à': 'a', 'ù': 'u', 'ç': 'c'
        }
        first = first.replace(char, replacements.get(char, ''))
        last = last.replace(char, replacements.get(char, ''))
    
    # Base username
    base_username = f"{first}.{last}" if first and last else email.split('@')[0]
    base_username = re.sub(r'[^a-z0-9._-]', '', base_username)
    
    # Vérifier unicité
    username = base_username
    counter = 1
    
    while Utilisateur.objects.filter(username=username).exists():
        counter += 1
        username = f"{base_username}{counter}"
    
    return username


def obtenir_ip_client(request):
    """
    Récupère l'adresse IP réelle du client
    Gère les proxy et load balancers
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    
    if x_forwarded_for:
        # Prendre la première IP (client réel)
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    
    return ip


def envoyer_email_bienvenue(user):
    """
    Envoie un email de bienvenue au nouvel utilisateur
    
    Contenu:
    - Message de bienvenue
    - Lien vers dashboard
    - Informations utiles
    - Support contact
    """
    try:
        subject = 'Bienvenue sur notre plateforme de gestion pharmacie'
        
        # Contexte pour le template
        context = {
            'user': user,
            'full_name': user.get_full_name(),
            'dashboard_url': f"{settings.SITE_URL}/compte/dashboard/",
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@example.com'),
            'site_name': getattr(settings, 'SITE_NAME', 'Gestion Pharmacie'),
        }
        
        # Render HTML et text
        html_message = render_to_string('gestion_compte/emails/bienvenue.html', context)
        text_message = strip_tags(html_message)
        
        # Envoyer
        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Email de bienvenue envoyé à {user.email}")
        return True
    
    except Exception as e:
        logger.error(f"Erreur envoi email à {user.email}: {e}")
        return False


def envoyer_email_activation(user, request):
    """
    Envoie un email d'activation avec token
    (Si vous voulez valider l'email avant activation)
    """
    try:
        from django.core.signing import Signer
        signer = Signer()
        token = signer.sign(str(user.id))
        
        activation_url = request.build_absolute_uri(
            f'/compte/activer/{token}/'
        )
        
        subject = 'Activez votre compte'
        
        context = {
            'user': user,
            'activation_url': activation_url,
            'site_name': getattr(settings, 'SITE_NAME', 'Gestion Pharmacie'),
        }
        
        html_message = render_to_string('gestion_compte/emails/activation.html', context)
        text_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Email d'activation envoyé à {user.email}")
        return True
    
    except Exception as e:
        logger.error(f"Erreur envoi email activation: {e}")
        return False


def valider_force_mot_de_passe(password):
    """
    Valide la force d'un mot de passe
    
    Critères:
    - Minimum 8 caractères
    - Au moins une majuscule
    - Au moins une minuscule
    - Au moins un chiffre
    - Au moins un caractère spécial (optionnel)
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Le mot de passe doit contenir au moins 8 caractères"
    
    if not re.search(r'[A-Z]', password):
        return False, "Le mot de passe doit contenir au moins une majuscule"
    
    if not re.search(r'[a-z]', password):
        return False, "Le mot de passe doit contenir au moins une minuscule"
    
    if not re.search(r'[0-9]', password):
        return False, "Le mot de passe doit contenir au moins un chiffre"
    
    # Optionnel: caractère spécial
    if getattr(settings, 'PASSWORD_REQUIRE_SPECIAL_CHAR', False):
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Le mot de passe doit contenir au moins un caractère spécial"
    
    return True, "Mot de passe valide"


# ============================================================================
# STATISTIQUES INSCRIPTION (Pour admin)
# ============================================================================

@login_required
@require_http_methods(["GET"])
def statistiques_inscriptions_view(request):
    """
    Vue des statistiques d'inscriptions (pour admin)
    """
    if not request.user.is_staff:
        messages.error(request, "Accès non autorisé")
        return redirect('gestion_compte:dashboard')
    
   
    
    # Inscriptions par jour (30 derniers jours)
    inscriptions_par_jour = Utilisateur.objects.filter(
        date_creation__gte=timezone.now() - timezone.timedelta(days=30)
    ).annotate(
        date=TruncDate('date_creation')
    ).values('date').annotate(
        total=Count('id')
    ).order_by('date')
    
    # Statistiques globales
    stats = {
        'total_utilisateurs': Utilisateur.objects.count(),
        'utilisateurs_actifs': Utilisateur.objects.filter(statut='actif').count(),
        'inscriptions_mois': Utilisateur.objects.filter(
            date_creation__month=timezone.now().month,
            date_creation__year=timezone.now().year
        ).count(),
        'inscriptions_semaine': Utilisateur.objects.filter(
            date_creation__gte=timezone.now() - timezone.timedelta(days=7)
        ).count(),
        'inscriptions_aujourd_hui': Utilisateur.objects.filter(
            date_creation__date=timezone.now().date()
        ).count(),
    }
    
    context = {
        'stats': stats,
        'inscriptions_par_jour': list(inscriptions_par_jour),
        'page_title': 'Statistiques Inscriptions',
    }
    
    return render(request, 'gestion_compte/stats_inscriptions.html', context)


# ============================================================================
# VUE DE CONNEXION PRINCIPALE
# ============================================================================

@never_cache
@require_http_methods(["GET", "POST"])
def connexion_view(request):
    """
    Vue de connexion complète avec sécurité et logging
    
    Fonctionnalités:
    - Vérification statut utilisateur
    - Détection tentatives multiples (blocage après 5 tentatives)
    - Logging des connexions (succès/échec)
    - Détection IP et User Agent
    - Gestion erreurs robuste
    - Messages informatifs
    - Redirection intelligente
    """
    
    # Redirection si déjà connecté
    if request.user.is_authenticated:
        messages.info(request, 'Vous êtes déjà connecté.')
        return redirect('gestion_compte:dashboard')
    
    if request.method == 'POST':
        form = ConnexionForm(request, data=request.POST)
        
        if form.is_valid():
            user = form.get_user()
            
            try:
                # ========================================
                # ÉTAPE 1: Vérifications de sécurité
                # ========================================
                
                # Vérifier si l'utilisateur peut se connecter
                if not user.peut_se_connecter():
                    # Enregistrer tentative échouée
                    enregistrer_historique_connexion(
                        request, 
                        user, 
                        succes=False, 
                        raison=f"Compte {user.get_statut_display()}"
                    )
                    
                    messages.error(
                        request, 
                        f'Compte {user.get_statut_display()}. '
                        f'Contactez l\'administrateur pour plus d\'informations.'
                    )
                    return redirect('gestion_compte:connexion')
                
                # Vérifier si le compte est bloqué (trop de tentatives)
                if user.statut == 'bloque':
                    messages.error(
                        request,
                        'Votre compte est bloqué suite à trop de tentatives de connexion échouées. '
                        'Veuillez contacter l\'administrateur.'
                    )
                    return redirect('gestion_compte:connexion')
                
                # ========================================
                # ÉTAPE 2: Connexion réussie
                # ========================================
                
                with transaction.atomic():
                    # Enregistrer l'historique de connexion
                    enregistrer_historique_connexion(
                        request, 
                        user, 
                        succes=True
                    )
                    
                    # Connexion de l'utilisateur
                    login(request, user)
                    
                    # Mettre à jour les informations de connexion
                    user.date_derniere_connexion = timezone.now()
                    user.ip_derniere_connexion = obtenir_ip_client(request)
                    user.reinitialiser_tentatives_connexion()
                    user.save(update_fields=[
                        'date_derniere_connexion',
                        'ip_derniere_connexion',
                        'tentatives_connexion'
                    ])
                    
                    # Logger la connexion
                    logger.info(
                        f"Connexion réussie: {user.email} "
                        f"(ID: {user.id}) depuis IP {user.ip_derniere_connexion}"
                    )
                
                # ========================================
                # ÉTAPE 3: Vérifications post-connexion
                # ========================================
                
                # CORRECTION: Vérifier si is_temporary_password existe
                # Si le champ existe, forcer changement de mot de passe
                if hasattr(user, 'is_temporary_password') and user.is_temporary_password:
                    messages.warning(
                        request,
                        'Vous devez changer votre mot de passe temporaire.'
                    )
                    return redirect('gestion_compte:changer_mot_de_passe')
                
                # Vérifier si le profil est complet
                if not user.telephone or not user.ville:
                    messages.info(
                        request,
                        'Veuillez compléter votre profil pour une meilleure expérience.'
                    )
                
                # ========================================
                # ÉTAPE 4: Redirection et message de bienvenue
                # ========================================
                
                # Message de bienvenue personnalisé
                heure = timezone.now().hour
                if heure < 12:
                    salutation = "Bonjour"
                elif heure < 18:
                    salutation = "Bon après-midi"
                else:
                    salutation = "Bonsoir"
                
                messages.success(
                    request,
                    f'{salutation} {user.get_full_name()} ! Connexion réussie.'
                )
                
                # Redirection intelligente
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                elif user.is_superuser or user.is_staff:
                    return redirect('admin:index')
                else:
                    return redirect('gestion_compte:dashboard')
            
            except Exception as e:
                logger.error(f"Erreur lors de la connexion: {e}", exc_info=True)
                messages.error(
                    request,
                    "Une erreur s'est produite lors de la connexion. "
                    "Veuillez réessayer."
                )
        
        else:
            # ========================================
            # Formulaire invalide (mauvais identifiants)
            # ========================================
            
            # Récupérer l'email pour incrémenter les tentatives
            email = request.POST.get('username', '').strip().lower()
            
            if email:
                try:
                    user = Utilisateur.objects.get(email__iexact=email)
                    
                    # Incrémenter tentatives de connexion
                    user.incrementer_tentatives_connexion()
                    
                    # Enregistrer tentative échouée
                    enregistrer_historique_connexion(
                        request,
                        user,
                        succes=False,
                        raison="Mot de passe incorrect"
                    )
                    
                    # Message adapté selon le nombre de tentatives
                    tentatives_restantes = 5 - user.tentatives_connexion
                    if tentatives_restantes > 0:
                        messages.error(
                            request,
                            f'Email ou mot de passe incorrect. '
                            f'Attention: {tentatives_restantes} tentative(s) restante(s) '
                            f'avant blocage du compte.'
                        )
                    else:
                        messages.error(
                            request,
                            'Votre compte a été bloqué suite à trop de tentatives échouées. '
                            'Contactez l\'administrateur.'
                        )
                    
                    logger.warning(
                        f"Tentative connexion échouée: {email} "
                        f"({user.tentatives_connexion}/5 tentatives)"
                    )
                
                except Utilisateur.DoesNotExist:
                    # Ne pas révéler que l'email n'existe pas (sécurité)
                    messages.error(request, 'Email ou mot de passe incorrect.')
                    logger.warning(f"Tentative connexion avec email inexistant: {email}")
            
            else:
                messages.error(request, 'Veuillez remplir tous les champs.')
    
    else:
        form = ConnexionForm()
    
    # Statistiques optionnelles pour la page
    stats = {
        'total_utilisateurs': Utilisateur.objects.filter(is_active=True).count(),
        'connexions_aujourd_hui': HistoriqueConnexion.objects.filter(
            date_connexion__date=timezone.now().date(),
            succes=True
        ).count(),
    }
    
    context = {
        'form': form,
        'stats': stats,
        'page_title': 'Connexion',
        'show_captcha': getattr(settings, 'ENABLE_CAPTCHA', False),
    }
    
    return render(request, 'gestion_compte/connexion.html', context)


# ============================================================================
# CONNEXION AJAX (Pour formulaires dynamiques)
# ============================================================================

@never_cache
@require_http_methods(["POST"])
def connexion_ajax_view(request):
    """
    Version AJAX de la connexion
    Retourne JSON pour intégration frontend moderne
    """
    
    if request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Vous êtes déjà connecté.'
        }, status=400)
    
    try:
        form = ConnexionForm(request, data=request.POST)
        
        if form.is_valid():
            user = form.get_user()
            
            # Vérifier statut
            if not user.peut_se_connecter():
                enregistrer_historique_connexion(request, user, succes=False)
                
                return JsonResponse({
                    'success': False,
                    'error': f'Compte {user.get_statut_display()}.'
                }, status=403)
            
            # Connexion
            with transaction.atomic():
                enregistrer_historique_connexion(request, user, succes=True)
                login(request, user)
                
                user.date_derniere_connexion = timezone.now()
                user.ip_derniere_connexion = obtenir_ip_client(request)
                user.reinitialiser_tentatives_connexion()
                user.save()
            
            logger.info(f"Connexion AJAX réussie: {user.email}")
            
            # Vérifier mot de passe temporaire
            need_password_change = (
                hasattr(user, 'is_temporary_password') and 
                user.is_temporary_password
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Bienvenue {user.get_full_name()} !',
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'full_name': user.get_full_name(),
                    'username': user.username,
                },
                'redirect_url': '/compte/changer-mot-de-passe/' if need_password_change else '/compte/dashboard/',
                'need_password_change': need_password_change
            })
        
        else:
            email = request.POST.get('username', '')
            
            if email:
                try:
                    user = Utilisateur.objects.get(email__iexact=email)
                    user.incrementer_tentatives_connexion()
                    enregistrer_historique_connexion(request, user, succes=False)
                    
                    tentatives_restantes = 5 - user.tentatives_connexion
                    
                    return JsonResponse({
                        'success': False,
                        'error': 'Email ou mot de passe incorrect.',
                        'tentatives_restantes': tentatives_restantes
                    }, status=401)
                
                except Utilisateur.DoesNotExist:
                    pass
            
            return JsonResponse({
                'success': False,
                'error': 'Email ou mot de passe incorrect.'
            }, status=401)
    
    except Exception as e:
        logger.error(f"Erreur connexion AJAX: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Une erreur inattendue s\'est produite.'
        }, status=500)

# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def obtenir_ip_client(request):
    """
    Récupère l'adresse IP réelle du client
    Gère les proxy et load balancers
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    
    if x_forwarded_for:
        # Prendre la première IP (client réel)
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
    
    return ip


def enregistrer_historique_connexion(request, user, succes=True, raison=''):
    """
    Enregistre l'historique de connexion
    
    Args:
        request: HttpRequest
        user: Utilisateur
        succes: bool - Si la connexion a réussi
        raison: str - Raison de l'échec (optionnel)
    """
    try:
        HistoriqueConnexion.objects.create(
            utilisateur=user,
            pharmacie=user.pharmacie_active,
            ip_address=obtenir_ip_client(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            succes=succes,
            raison_echec=raison if not succes else ''
        )
    except Exception as e:
        logger.error(f"Erreur enregistrement historique: {e}")


def verifier_compte_actif(user):
    """
    Vérifie si le compte est actif et peut se connecter
    
    Returns:
        tuple: (is_active, error_message)
    """
    if not user.is_active:
        return False, "Compte désactivé. Contactez l'administrateur."
    
    if user.statut != 'actif':
        statut_messages = {
            'suspendu': 'Compte suspendu.',
            'bloque': 'Compte bloqué suite à trop de tentatives échouées.',
            'desactive': 'Compte désactivé.',
        }
        return False, statut_messages.get(user.statut, 'Compte non actif.')
    
    return True, ''


# ============================================================================
# STATISTIQUES CONNEXIONS (Pour admin)
# ============================================================================

@login_required
@require_http_methods(["GET"])
def statistiques_connexions_view(request):
    """
    Vue des statistiques de connexions (pour admin)
    """
    if not request.user.is_staff:
        messages.error(request, "Accès non autorisé")
        return redirect('gestion_compte:dashboard')
    
    
    # Connexions par jour (30 derniers jours)
    connexions_par_jour = HistoriqueConnexion.objects.filter(
        date_connexion__gte=timezone.now() - timezone.timedelta(days=30),
        succes=True
    ).annotate(
        date=TruncDate('date_connexion')
    ).values('date').annotate(
        total=Count('id')
    ).order_by('date')
    
    # Statistiques globales
    stats = {
        'total_connexions': HistoriqueConnexion.objects.filter(succes=True).count(),
        'connexions_mois': HistoriqueConnexion.objects.filter(
            date_connexion__month=timezone.now().month,
            date_connexion__year=timezone.now().year,
            succes=True
        ).count(),
        'connexions_semaine': HistoriqueConnexion.objects.filter(
            date_connexion__gte=timezone.now() - timezone.timedelta(days=7),
            succes=True
        ).count(),
        'connexions_aujourd_hui': HistoriqueConnexion.objects.filter(
            date_connexion__date=timezone.now().date(),
            succes=True
        ).count(),
        'tentatives_echouees_mois': HistoriqueConnexion.objects.filter(
            date_connexion__month=timezone.now().month,
            date_connexion__year=timezone.now().year,
            succes=False
        ).count(),
        'comptes_bloques': Utilisateur.objects.filter(statut='bloque').count(),
    }
    
    context = {
        'stats': stats,
        'connexions_par_jour': list(connexions_par_jour),
        'page_title': 'Statistiques Connexions',
    }
    
    return render(request, 'gestion_compte/stats_connexions.html', context)



# ============================================================================
# VUE DÉCONNEXION PRINCIPALE
# ============================================================================

@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def deconnexion_view(request):
    """
    Vue de déconnexion complète avec:
    - Enregistrement historique
    - Logging
    - Nettoyage session
    - Message personnalisé
    - Page de confirmation (optionnel)
    """
    
    # ========================================
    # OPTION 1: Déconnexion immédiate (GET)
    # ========================================
    if request.method == 'GET' and not getattr(settings, 'LOGOUT_CONFIRMATION_REQUIRED', False):
        return process_logout(request)
    
    # ========================================
    # OPTION 2: Page de confirmation (GET)
    # ========================================
    if request.method == 'GET':
        return render(request, 'gestion_compte/deconnexion_confirmation.html', {
            'user': request.user,
            'page_title': 'Déconnexion',
        })
    
    # ========================================
    # OPTION 3: Déconnexion après confirmation (POST)
    # ========================================
    if request.method == 'POST':
        return process_logout(request)


def process_logout(request):
    """
    Traite la déconnexion de l'utilisateur
    
    Étapes:
    1. Sauvegarder les infos utilisateur
    2. Enregistrer l'historique
    3. Logger l'action
    4. Nettoyer la session
    5. Déconnecter
    6. Rediriger avec message
    """
    
    try:
        # ========================================
        # ÉTAPE 1: Sauvegarder les infos avant déconnexion
        # ========================================
        user = request.user
        user_name = user.get_full_name()
        user_email = user.email
        user_id = str(user.id)
        
        # Calculer durée de session
        session_start = request.session.get('session_start_time')
        session_duration = None
        
        if session_start:
            from datetime import datetime
            start_time = datetime.fromisoformat(session_start)
            session_duration = (timezone.now() - start_time).total_seconds()
        
        # ========================================
        # ÉTAPE 2: Enregistrer dans l'historique
        # ========================================
        try:
            from .models import HistoriqueConnexion
            
            # Mettre à jour la dernière connexion
            derniere_connexion = HistoriqueConnexion.objects.filter(
                utilisateur=user,
                succes=True,
                date_deconnexion__isnull=True
            ).order_by('-date_connexion').first()
            
            if derniere_connexion:
                derniere_connexion.date_deconnexion = timezone.now()
                
                if session_duration:
                    derniere_connexion.duree_session = int(session_duration)
                
                derniere_connexion.save(update_fields=['date_deconnexion', 'duree_session'])
                
                logger.info(
                    f"Historique déconnexion enregistré: {user_email} "
                    f"(durée: {format_duration(session_duration)})"
                )
        
        except (ImportError, AttributeError) as e:
            logger.warning(f"Impossible d'enregistrer l'historique: {e}")
        
        # ========================================
        # ÉTAPE 3: Mettre à jour l'utilisateur
        # ========================================
        try:
            with transaction.atomic():
                # Mettre à jour date dernière activité
                user.date_derniere_connexion = timezone.now()
                user.save(update_fields=['date_derniere_connexion'])
        
        except Exception as e:
            logger.error(f"Erreur mise à jour utilisateur: {e}")
        
        # ========================================
        # ÉTAPE 4: Logger la déconnexion
        # ========================================
        logger.info(
            f"Déconnexion: {user_name} ({user_email}) "
            f"depuis IP {obtenir_ip_client(request)}"
        )
        
        # ========================================
        # ÉTAPE 5: Nettoyer la session
        # ========================================
        # Sauvegarder les messages avant de vider
        storage = messages.get_messages(request)
        storage.used = False  # Garder les messages
        
        # Vider la session mais garder certaines infos
        session_keys_to_keep = getattr(settings, 'LOGOUT_KEEP_SESSION_KEYS', [])
        session_backup = {key: request.session.get(key) for key in session_keys_to_keep}
        
        # Vider la session
        request.session.flush()
        
        # Restaurer les clés à garder
        for key, value in session_backup.items():
            if value is not None:
                request.session[key] = value
        
        # ========================================
        # ÉTAPE 6: Déconnecter l'utilisateur
        # ========================================
        logout(request)
        
        # ========================================
        # ÉTAPE 7: Message personnalisé
        # ========================================
        heure = timezone.now().hour
        
        if heure < 12:
            salutation = "Bonne journée"
        elif heure < 18:
            salutation = "Bonne fin de journée"
        else:
            salutation = "Bonne soirée"
        
        messages.success(
            request,
            f'Au revoir {user_name} ! Vous avez été déconnecté avec succès. {salutation} !'
        )
        
        # Ajouter info durée session si disponible
        if session_duration:
            duree_formatee = format_duration(session_duration)
            messages.info(
                request,
                f'Durée de votre session : {duree_formatee}'
            )
        
        # ========================================
        # ÉTAPE 8: Redirection
        # ========================================
        # URL de redirection personnalisée
        redirect_url = request.GET.get('next')
        
        if redirect_url and is_safe_url(redirect_url, request):
            return redirect(redirect_url)
        
        # Redirection par défaut
        return redirect(
            getattr(settings, 'LOGOUT_REDIRECT_URL', 'gestion_compte:connexion')
        )
    
    except Exception as e:
        logger.error(f"Erreur lors de la déconnexion: {e}", exc_info=True)
        
        # Déconnexion forcée même en cas d'erreur
        logout(request)
        
        messages.warning(
            request,
            'Vous avez été déconnecté, mais une erreur s\'est produite lors du traitement.'
        )
        
        return redirect('gestion_compte:connexion')

# ============================================================================
# DÉCONNEXION DE TOUS LES APPAREILS
# ============================================================================

@never_cache
@login_required
@require_http_methods(["POST"])
def deconnexion_tous_appareils_view(request):
    """
    Déconnecte l'utilisateur de tous les appareils
    En supprimant toutes ses sessions
    """
    
    try:
        from django.contrib.sessions.models import Session
        from django.contrib.auth import get_user_model
        
        user = request.user
        user_id = str(user.id)
        
        # Récupérer toutes les sessions actives de l'utilisateur
        sessions_supprimees = 0
        
        for session in Session.objects.all():
            session_data = session.get_decoded()
            if session_data.get('_auth_user_id') == user_id:
                session.delete()
                sessions_supprimees += 1
        
        logger.info(
            f"Déconnexion tous appareils: {user.email} "
            f"({sessions_supprimees} sessions supprimées)"
        )
        
        messages.success(
            request,
            f'Vous avez été déconnecté de tous vos appareils ({sessions_supprimees} sessions).'
        )
        
        return redirect('gestion_compte:connexion')
    
    except Exception as e:
        logger.error(f"Erreur déconnexion tous appareils: {e}", exc_info=True)
        
        logout(request)
        messages.error(request, 'Erreur lors de la déconnexion de tous les appareils.')
        
        return redirect('gestion_compte:connexion')


# ============================================================================
# DÉCONNEXION AJAX
# ============================================================================

@never_cache
@login_required
@require_http_methods(["POST"])
def deconnexion_ajax_view(request):
    """
    Version AJAX de la déconnexion
    Retourne JSON pour applications modernes
    """
    
    try:
        user = request.user
        user_name = user.get_full_name()
        
        # Logger
        logger.info(f"Déconnexion AJAX: {user.email}")
        
        # Déconnecter
        logout(request)
        
        return JsonResponse({
            'success': True,
            'message': f'Au revoir {user_name} !',
            'redirect_url': '/connexion/'
        })
    
    except Exception as e:
        logger.error(f"Erreur déconnexion AJAX: {e}")
        
        return JsonResponse({
            'success': False,
            'error': 'Erreur lors de la déconnexion'
        }, status=500)


# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def obtenir_ip_client(request):
    """Récupère l'IP réelle du client"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
    
    return ip


def format_duration(seconds):
    """
    Formate une durée en secondes en format lisible
    
    Exemples:
    - 65 → "1 minute 5 secondes"
    - 3600 → "1 heure"
    - 7265 → "2 heures 1 minute"
    """
    if not seconds:
        return "0 seconde"
    
    seconds = int(seconds)
    
    heures = seconds // 3600
    minutes = (seconds % 3600) // 60
    secondes = seconds % 60
    
    parts = []
    
    if heures > 0:
        parts.append(f"{heures} heure{'s' if heures > 1 else ''}")
    
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
    
    if secondes > 0 and not heures:  # Afficher secondes seulement si < 1h
        parts.append(f"{secondes} seconde{'s' if secondes > 1 else ''}")
    
    return ' '.join(parts)


def is_safe_url(url, request):
    """
    Vérifie si l'URL de redirection est sûre
    Empêche les redirections malveillantes
    """
    from urllib.parse import urlparse
    
    if not url:
        return False
    
    # URL relative = sûre
    if url.startswith('/'):
        return True
    
    # Vérifier le domaine
    parsed = urlparse(url)
    
    if not parsed.netloc:
        return True
    
    # Vérifier que c'est le même domaine
    request_host = request.get_host()
    
    return parsed.netloc == request_host


# ============================================================================
# VUE STATISTIQUES DÉCONNEXIONS (Admin)
# ============================================================================

@login_required
@require_http_methods(["GET"])
def statistiques_deconnexions_view(request):
    """
    Statistiques des déconnexions (pour admin)
    """
    if not request.user.is_staff:
        messages.error(request, "Accès non autorisé")
        return redirect('gestion_compte:dashboard')
    
    try:
        from django.db.models import Avg, Count
        from django.db.models.functions import TruncDate
        from .models import HistoriqueConnexion
        
        # Sessions aujourd'hui
        aujourd_hui = timezone.now().date()
        
        sessions_aujourd_hui = HistoriqueConnexion.objects.filter(
            date_connexion__date=aujourd_hui,
            succes=True
        )
        
        # Statistiques
        stats = {
            'sessions_actives': HistoriqueConnexion.objects.filter(
                date_deconnexion__isnull=True,
                succes=True
            ).count(),
            
            'sessions_aujourd_hui': sessions_aujourd_hui.count(),
            
            'deconnexions_aujourd_hui': HistoriqueConnexion.objects.filter(
                date_deconnexion__date=aujourd_hui
            ).count(),
            
            'duree_moyenne_session': HistoriqueConnexion.objects.filter(
                duree_session__isnull=False
            ).aggregate(
                avg=Avg('duree_session')
            )['avg'] or 0,
        }
        
        # Durée moyenne formatée
        stats['duree_moyenne_formatee'] = format_duration(stats['duree_moyenne_session'])
        
        # Déconnexions par jour (30 derniers jours)
        deconnexions_par_jour = HistoriqueConnexion.objects.filter(
            date_deconnexion__gte=timezone.now() - timezone.timedelta(days=30),
            date_deconnexion__isnull=False
        ).annotate(
            date=TruncDate('date_deconnexion')
        ).values('date').annotate(
            total=Count('id')
        ).order_by('date')
        
        context = {
            'stats': stats,
            'deconnexions_par_jour': list(deconnexions_par_jour),
            'page_title': 'Statistiques Déconnexions',
        }
        
        return render(request, 'gestion_compte/stats_deconnexions.html', context)
    
    except Exception as e:
        logger.error(f"Erreur stats déconnexions: {e}", exc_info=True)
        messages.error(request, "Erreur lors du chargement des statistiques")
        return redirect('gestion_compte:dashboard')



# ==================== VUES PHARMACIE ====================

@login_required
def pharmacie_detail(request, pharmacie_id=None):
    """
    Affiche les détails d'une pharmacie
    Si pharmacie_id n'est pas fourni, affiche la pharmacie active de l'utilisateur
    """
    if pharmacie_id:
        pharmacie = get_object_or_404(Pharmacie, id=pharmacie_id)
        # Vérifier les permissions
        if not (request.user.is_superuser or 
                pharmacie.proprietaire == request.user or
                request.user.pharmacie_active == pharmacie):
            messages.error(request, "Vous n'avez pas accès à cette pharmacie.")
            return redirect('gestion_compte:dashboard')
    else:
        pharmacie = request.user.pharmacie_active
        if not pharmacie:
            messages.warning(request, "Aucune pharmacie active. Veuillez en sélectionner une.")
            return redirect('gestion_compte:pharmacie_liste')
    
    # Statistiques de la pharmacie
    stats = {
        'total_employes': Utilisateur.objects.filter(pharmacie_active=pharmacie).count(),
        'employes_actifs': Utilisateur.objects.filter(
            pharmacie_active=pharmacie, 
            statut='actif'
        ).count(),
        'completion': pharmacie.pourcentage_completion,
        'est_complete': pharmacie.configuration_complete,
    }
    
    context = {
        'pharmacie': pharmacie,
        'stats': stats,
        'est_proprietaire': pharmacie.proprietaire == request.user,
        'peut_modifier': request.user.is_superuser or pharmacie.proprietaire == request.user,
    }
    
    return render(request, 'gestion_compte/pharmacie_detail.html', context)


@login_required
def pharmacie_liste(request):
    """
    Liste toutes les pharmacies accessibles par l'utilisateur
    """
    # Filtrage selon le rôle
    if request.user.is_superuser:
        pharmacies = Pharmacie.objects.all()
    else:
        pharmacies = Pharmacie.objects.filter(
            Q(proprietaire=request.user) | 
            Q(utilisateurs_actifs=request.user)
        ).distinct()
    
    # Recherche
    search_query = request.GET.get('search', '')
    if search_query:
        pharmacies = pharmacies.filter(
            Q(nom_commercial__icontains=search_query) |
            Q(code__icontains=search_query) |
            Q(ville__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Filtrage par statut
    statut_filter = request.GET.get('statut', '')
    if statut_filter:
        pharmacies = pharmacies.filter(statut=statut_filter)
    
    # Tri
    sort_by = request.GET.get('sort', '-date_creation')
    pharmacies = pharmacies.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(pharmacies, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'statut_filter': statut_filter,
        'sort_by': sort_by,
        'statut_choices': Pharmacie.STATUT_CHOICES,
    }
    
    return render(request, 'gestion_compte/pharmacie_liste.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def pharmacie_creer(request):
    """
    Créer une nouvelle pharmacie
    """
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Récupération des données du formulaire
                data = request.POST
                
                # Validation des champs obligatoires
                champs_obligatoires = [
                    'nom_commercial', 'adresse', 'ville', 
                    'telephone_principal', 'email', 'numero_autorisation'
                ]
                
                for champ in champs_obligatoires:
                    if not data.get(champ):
                        messages.error(request, f"Le champ {champ.replace('_', ' ')} est obligatoire.")
                        return redirect('gestion_compte:pharmacie_creer')
                
                # Création de la pharmacie
                pharmacie = Pharmacie.objects.create(
                    nom_commercial=data.get('nom_commercial'),
                    slogan=data.get('slogan', ''),
                    adresse=data.get('adresse'),
                    ville=data.get('ville'),
                    region=data.get('region', ''),
                    pays=data.get('pays', 'Cameroun'),
                    code_postal=data.get('code_postal', ''),
                    telephone_principal=data.get('telephone_principal'),
                    telephone_secondaire=data.get('telephone_secondaire', ''),
                    email=data.get('email'),
                    whatsapp=data.get('whatsapp', ''),
                    site_web=data.get('site_web', ''),
                    numero_autorisation=data.get('numero_autorisation'),
                    nif=data.get('nif', ''),
                    rccm=data.get('rccm', ''),
                    devise=data.get('devise', 'XAF'),
                    symbole_devise=data.get('symbole_devise', 'FCFA'),
                    taux_tva=data.get('taux_tva', 19.25),
                    fuseau_horaire=data.get('fuseau_horaire', 'Africa/Douala'),
                    proprietaire=request.user,
                )
                
                # Gestion du logo
                if request.FILES.get('logo'):
                    pharmacie.logo = request.FILES['logo']
                    pharmacie.save()
                
                # Gestion des coordonnées GPS
                if data.get('latitude') and data.get('longitude'):
                    pharmacie.latitude = data.get('latitude')
                    pharmacie.longitude = data.get('longitude')
                    pharmacie.save()
                
                # Définir comme pharmacie active si l'utilisateur n'en a pas
                if not request.user.pharmacie_active:
                    request.user.pharmacie_active = pharmacie
                    request.user.save()
                
                messages.success(request, f"La pharmacie '{pharmacie.nom_commercial}' a été créée avec succès!")
                return redirect('gestion_compte:pharmacie_detail', pharmacie_id=pharmacie.id)
                
        except Exception as e:
            messages.error(request, f"Erreur lors de la création de la pharmacie: {str(e)}")
            return redirect('gestion_compte:pharmacie_creer')
    
    # GET request
    context = {
        'fuseaux_horaires': [
            'Africa/Douala', 'Africa/Kinshasa', 'Africa/Lagos',
            'Africa/Dakar', 'Africa/Abidjan', 'Africa/Accra'
        ],
    }
    return render(request, 'gestion_compte/pharmacie_form.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def pharmacie_modifier(request, pharmacie_id):
    """
    Modifier une pharmacie existante
    """
    pharmacie = get_object_or_404(Pharmacie, id=pharmacie_id)
    
    # Vérifier les permissions
    if not (request.user.is_superuser or pharmacie.proprietaire == request.user):
        messages.error(request, "Vous n'avez pas la permission de modifier cette pharmacie.")
        return redirect('gestion_compte:pharmacie_detail', pharmacie_id=pharmacie_id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                data = request.POST
                
                # Mise à jour des champs
                pharmacie.nom_commercial = data.get('nom_commercial', pharmacie.nom_commercial)
                pharmacie.slogan = data.get('slogan', '')
                pharmacie.adresse = data.get('adresse', pharmacie.adresse)
                pharmacie.ville = data.get('ville', pharmacie.ville)
                pharmacie.region = data.get('region', '')
                pharmacie.pays = data.get('pays', 'Cameroun')
                pharmacie.code_postal = data.get('code_postal', '')
                
                # Coordonnées GPS
                if data.get('latitude'):
                    pharmacie.latitude = data.get('latitude')
                if data.get('longitude'):
                    pharmacie.longitude = data.get('longitude')
                
                # Contact
                pharmacie.telephone_principal = data.get('telephone_principal', pharmacie.telephone_principal)
                pharmacie.telephone_secondaire = data.get('telephone_secondaire', '')
                pharmacie.email = data.get('email', pharmacie.email)
                pharmacie.whatsapp = data.get('whatsapp', '')
                pharmacie.site_web = data.get('site_web', '')
                
                # Informations légales
                pharmacie.numero_autorisation = data.get('numero_autorisation', pharmacie.numero_autorisation)
                pharmacie.nif = data.get('nif', '')
                pharmacie.rccm = data.get('rccm', '')
                
                # Paramètres
                pharmacie.devise = data.get('devise', 'XAF')
                pharmacie.symbole_devise = data.get('symbole_devise', 'FCFA')
                pharmacie.taux_tva = data.get('taux_tva', 19.25)
                pharmacie.fuseau_horaire = data.get('fuseau_horaire', 'Africa/Douala')
                
                # Gestion du logo
                if request.FILES.get('logo'):
                    pharmacie.logo = request.FILES['logo']
                
                pharmacie.save()
                
                messages.success(request, "La pharmacie a été mise à jour avec succès!")
                return redirect('gestion_compte:pharmacie_detail', pharmacie_id=pharmacie_id)
                
        except Exception as e:
            messages.error(request, f"Erreur lors de la mise à jour: {str(e)}")
    
    context = {
        'pharmacie': pharmacie,
        'mode': 'modifier',
        'fuseaux_horaires': [
            'Africa/Douala', 'Africa/Kinshasa', 'Africa/Lagos',
            'Africa/Dakar', 'Africa/Abidjan', 'Africa/Accra'
        ],
    }
    return render(request, 'gestion_compte/pharmacie_form.html', context)


@login_required
@require_http_methods(["POST"])
def pharmacie_changer_statut(request, pharmacie_id):
    """
    Changer le statut d'une pharmacie
    """
    pharmacie = get_object_or_404(Pharmacie, id=pharmacie_id)
    
    # Vérifier les permissions
    if not (request.user.is_superuser or pharmacie.proprietaire == request.user):
        return JsonResponse({'success': False, 'message': 'Permission refusée'}, status=403)
    
    nouveau_statut = request.POST.get('statut')
    
    if nouveau_statut not in dict(Pharmacie.STATUT_CHOICES):
        return JsonResponse({'success': False, 'message': 'Statut invalide'}, status=400)
    
    pharmacie.statut = nouveau_statut
    pharmacie.save()
    
    return JsonResponse({
        'success': True,
        'message': f'Statut changé en "{pharmacie.get_statut_display()}"',
        'nouveau_statut': nouveau_statut
    })


@login_required
def pharmacie_selectionner(request, pharmacie_id):
    """
    Définir une pharmacie comme pharmacie active pour l'utilisateur
    """
    pharmacie = get_object_or_404(Pharmacie, id=pharmacie_id)
    
    # Vérifier que l'utilisateur a accès à cette pharmacie
    if not (request.user.is_superuser or 
            pharmacie.proprietaire == request.user or
            Utilisateur.objects.filter(id=request.user.id, pharmacie_active=pharmacie).exists()):
        messages.error(request, "Vous n'avez pas accès à cette pharmacie.")
        return redirect('gestion_compte:pharmacie_liste')
    
    request.user.pharmacie_active = pharmacie
    request.user.save()
    
    messages.success(request, f"Pharmacie active: {pharmacie.nom_commercial}")
    return redirect('gestion_compte:dashboard')



# ==================== VUES UTILISATEUR ====================

@login_required
def utilisateur_liste(request):
    """
    Liste des utilisateurs (employés) de la pharmacie active
    """
    pharmacie_active = request.user.pharmacie_active
    
    if not pharmacie_active:
        messages.warning(request, "Veuillez sélectionner une pharmacie active.")
        return redirect('gestion_compte:pharmacie_liste')
    
    # Filtrage de base
    utilisateurs = Utilisateur.objects.filter(pharmacie_active=pharmacie_active)
    
    # Recherche
    search_query = request.GET.get('search', '')
    if search_query:
        utilisateurs = utilisateurs.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(telephone__icontains=search_query)
        )
    
    # Filtrage par statut
    statut_filter = request.GET.get('statut', '')
    if statut_filter:
        utilisateurs = utilisateurs.filter(statut=statut_filter)
    
    # Tri
    sort_by = request.GET.get('sort', '-date_creation')
    utilisateurs = utilisateurs.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(utilisateurs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistiques
    stats = {
        'total': utilisateurs.count(),
        'actifs': utilisateurs.filter(statut='actif').count(),
        'suspendus': utilisateurs.filter(statut='suspendu').count(),
        'bloques': utilisateurs.filter(statut='bloque').count(),
    }
    
    context = {
        'page_obj': page_obj,
        'stats': stats,
        'search_query': search_query,
        'statut_filter': statut_filter,
        'sort_by': sort_by,
        'statut_choices': Utilisateur.STATUT_CHOICES,
        'pharmacie_active': pharmacie_active,
    }
    
    return render(request, 'gestion_compte/utilisateur_liste.html', context)


@login_required
def utilisateur_detail(request, utilisateur_id):
    """
    Affiche les détails d'un utilisateur
    """
    utilisateur = get_object_or_404(Utilisateur, id=utilisateur_id)
    pharmacie_active = request.user.pharmacie_active
    
    # Vérifier les permissions
    if not (request.user.is_superuser or 
            request.user == utilisateur or
            (pharmacie_active and utilisateur.pharmacie_active == pharmacie_active)):
        messages.error(request, "Vous n'avez pas accès à ce profil.")
        return redirect('gestion_compte:dashboard')
    
    # Historique récent (à implémenter selon vos besoins)
    activites_recentes = []
    
    context = {
        'utilisateur': utilisateur,
        'activites_recentes': activites_recentes,
        'peut_modifier': request.user.is_superuser or request.user == utilisateur,
        'est_proprietaire': pharmacie_active and pharmacie_active.proprietaire == request.user,
    }
    
    return render(request, 'gestion_compte/utilisateur_detail.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def utilisateur_creer(request):
    """
    Créer un nouvel utilisateur (employé)
    """
    pharmacie_active = request.user.pharmacie_active
    
    if not pharmacie_active:
        messages.warning(request, "Veuillez sélectionner une pharmacie active.")
        return redirect('gestion_compte:pharmacie_liste')
    
    # Vérifier les permissions (seul le propriétaire ou superuser peut créer)
    if not (request.user.is_superuser or pharmacie_active.proprietaire == request.user):
        messages.error(request, "Vous n'avez pas la permission de créer des utilisateurs.")
        return redirect('gestion_compte:utilisateur_liste')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                data = request.POST
                
                # Validation des champs obligatoires
                if not data.get('email'):
                    messages.error(request, "L'email est obligatoire.")
                    return redirect('gestion_compte:utilisateur_creer')
                
                if not data.get('first_name') or not data.get('last_name'):
                    messages.error(request, "Le prénom et le nom sont obligatoires.")
                    return redirect('gestion_compte:utilisateur_creer')
                
                # Vérifier si l'email existe déjà
                if Utilisateur.objects.filter(email=data.get('email')).exists():
                    messages.error(request, "Un utilisateur avec cet email existe déjà.")
                    return redirect('gestion_compte:utilisateur_creer')
                
                # Création de l'utilisateur
                utilisateur = Utilisateur.objects.create_user(
                    email=data.get('email'),
                    password=data.get('password', 'ChangeMe123!'),
                    first_name=data.get('first_name'),
                    last_name=data.get('last_name'),
                    telephone=data.get('telephone', ''),
                    whatsapp=data.get('whatsapp', ''),
                    date_naissance=data.get('date_naissance') or None,
                    adresse=data.get('adresse', ''),
                    ville=data.get('ville', ''),
                    pays=data.get('pays', 'Cameroun'),
                    pharmacie_active=pharmacie_active,
                    cree_par=request.user,
                )
                
                # Gestion de la photo
                if request.FILES.get('photo'):
                    utilisateur.photo = request.FILES['photo']
                    utilisateur.save()
                
                messages.success(
                    request, 
                    f"L'utilisateur {utilisateur.get_full_name()} a été créé avec succès!"
                )
                return redirect('gestion_compte:utilisateur_detail', utilisateur_id=utilisateur.id)
                
        except Exception as e:
            messages.error(request, f"Erreur lors de la création: {str(e)}")
    
    context = {
        'pharmacie_active': pharmacie_active,
    }
    return render(request, 'gestion_compte/utilisateur_form.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def utilisateur_modifier(request, utilisateur_id):
    """
    Modifier un utilisateur existant
    """
    utilisateur = get_object_or_404(Utilisateur, id=utilisateur_id)
    pharmacie_active = request.user.pharmacie_active
    
    # Vérifier les permissions
    peut_modifier = (
        request.user.is_superuser or 
        request.user == utilisateur or
        (pharmacie_active and pharmacie_active.proprietaire == request.user)
    )
    
    if not peut_modifier:
        messages.error(request, "Vous n'avez pas la permission de modifier cet utilisateur.")
        return redirect('gestion_compte:utilisateur_detail', utilisateur_id=utilisateur_id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                data = request.POST
                
                # Mise à jour des informations de base
                utilisateur.first_name = data.get('first_name', utilisateur.first_name)
                utilisateur.last_name = data.get('last_name', utilisateur.last_name)
                utilisateur.telephone = data.get('telephone', '')
                utilisateur.whatsapp = data.get('whatsapp', '')
                utilisateur.adresse = data.get('adresse', '')
                utilisateur.ville = data.get('ville', '')
                utilisateur.pays = data.get('pays', 'Cameroun')
                
                # Date de naissance
                if data.get('date_naissance'):
                    utilisateur.date_naissance = data.get('date_naissance')
                
                # Gestion de la photo
                if request.FILES.get('photo'):
                    utilisateur.photo = request.FILES['photo']
                
                # Changement de mot de passe
                if data.get('nouveau_password'):
                    if data.get('nouveau_password') == data.get('confirmer_password'):
                        utilisateur.set_password(data.get('nouveau_password'))
                        messages.info(request, "Le mot de passe a été modifié.")
                    else:
                        messages.warning(request, "Les mots de passe ne correspondent pas.")
                
                utilisateur.save()
                
                messages.success(request, "Le profil a été mis à jour avec succès!")
                return redirect('gestion_compte:utilisateur_detail', utilisateur_id=utilisateur_id)
                
        except Exception as e:
            messages.error(request, f"Erreur lors de la mise à jour: {str(e)}")
    
    context = {
        'utilisateur': utilisateur,
        'mode': 'modifier',
        'est_proprietaire': pharmacie_active and pharmacie_active.proprietaire == request.user,
    }
    return render(request, 'gestion_compte/utilisateur_form.html', context)


@login_required
@require_http_methods(["POST"])
def utilisateur_changer_statut(request, utilisateur_id):
    """
    Changer le statut d'un utilisateur
    """
    utilisateur = get_object_or_404(Utilisateur, id=utilisateur_id)
    pharmacie_active = request.user.pharmacie_active
    
    # Vérifier les permissions
    if not (request.user.is_superuser or 
            (pharmacie_active and pharmacie_active.proprietaire == request.user)):
        return JsonResponse({'success': False, 'message': 'Permission refusée'}, status=403)
    
    nouveau_statut = request.POST.get('statut')
    raison = request.POST.get('raison', '')
    
    if nouveau_statut not in dict(Utilisateur.STATUT_CHOICES):
        return JsonResponse({'success': False, 'message': 'Statut invalide'}, status=400)
    
    utilisateur.statut = nouveau_statut
    utilisateur.raison_statut = raison
    utilisateur.date_changement_statut = timezone.now()
    utilisateur.save()
    
    return JsonResponse({
        'success': True,
        'message': f'Statut changé en "{utilisateur.get_statut_display()}"',
        'nouveau_statut': nouveau_statut
    })


@login_required
@require_http_methods(["POST"])
def utilisateur_reinitialiser_tentatives(request, utilisateur_id):
    """
    Réinitialiser les tentatives de connexion d'un utilisateur
    """
    utilisateur = get_object_or_404(Utilisateur, id=utilisateur_id)
    pharmacie_active = request.user.pharmacie_active
    
    # Vérifier les permissions
    if not (request.user.is_superuser or 
            (pharmacie_active and pharmacie_active.proprietaire == request.user)):
        return JsonResponse({'success': False, 'message': 'Permission refusée'}, status=403)
    
    utilisateur.reinitialiser_tentatives_connexion()
    
    # Si l'utilisateur était bloqué, le réactiver
    if utilisateur.statut == 'bloque':
        utilisateur.statut = 'actif'
        utilisateur.raison_statut = ''
        utilisateur.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Les tentatives de connexion ont été réinitialisées'
    })


# ==================== VUE PARAMÈTRES COMPTE ====================

@login_required
def parametres_compte(request):
    """
    Vue principale pour les paramètres du compte
    Affiche les informations de la pharmacie et de l'utilisateur
    """
    pharmacie_active = request.user.pharmacie_active
    
    if not pharmacie_active:
        messages.warning(request, "Veuillez sélectionner une pharmacie active.")
        return redirect('gestion_compte:pharmacie_liste')
    
    # Statistiques de la pharmacie
    stats_pharmacie = {
        'total_employes': Utilisateur.objects.filter(pharmacie_active=pharmacie_active).count(),
        'employes_actifs': Utilisateur.objects.filter(
            pharmacie_active=pharmacie_active, 
            statut='actif'
        ).count(),
        'employes_suspendus': Utilisateur.objects.filter(
            pharmacie_active=pharmacie_active, 
            statut='suspendu'
        ).count(),
        'completion': pharmacie_active.pourcentage_completion,
        'est_complete': pharmacie_active.configuration_complete,
    }
    
    # Liste des employés récents
    employes_recents = Utilisateur.objects.filter(
        pharmacie_active=pharmacie_active
    ).order_by('-date_creation')[:5]
    
    context = {
        'pharmacie': pharmacie_active,
        'utilisateur': request.user,
        'stats_pharmacie': stats_pharmacie,
        'employes_recents': employes_recents,
        'est_proprietaire': pharmacie_active.proprietaire == request.user,
        'peut_modifier_pharmacie': request.user.is_superuser or pharmacie_active.proprietaire == request.user,
    }
    
    return render(request, 'gestion_compte/parametres_compte.html', context)


@login_required
def mon_profil(request):
    """
    Vue du profil personnel de l'utilisateur connecté
    """
    return utilisateur_detail(request, request.user.id)


@login_required
@require_http_methods(["GET", "POST"])
def mon_profil_modifier(request):
    """
    Modifier son propre profil
    """
    return utilisateur_modifier(request, request.user.id)


# ==================== VUES AJAX / API ====================

@login_required
def pharmacie_completion_ajax(request, pharmacie_id):
    """
    Retourne le pourcentage de complétion d'une pharmacie (AJAX)
    """
    pharmacie = get_object_or_404(Pharmacie, id=pharmacie_id)
    
    return JsonResponse({
        'completion': pharmacie.pourcentage_completion,
        'est_complete': pharmacie.configuration_complete,
    })


@login_required
def utilisateur_stats_ajax(request):
    """
    Retourne les statistiques des utilisateurs de la pharmacie active (AJAX)
    """
    pharmacie_active = request.user.pharmacie_active
    
    if not pharmacie_active:
        return JsonResponse({'error': 'Aucune pharmacie active'}, status=400)
    
    stats = {
        'total': Utilisateur.objects.filter(pharmacie_active=pharmacie_active).count(),
        'actifs': Utilisateur.objects.filter(
            pharmacie_active=pharmacie_active, 
            statut='actif'
        ).count(),
        'suspendus': Utilisateur.objects.filter(
            pharmacie_active=pharmacie_active, 
            statut='suspendu'
        ).count(),
        'bloques': Utilisateur.objects.filter(
            pharmacie_active=pharmacie_active, 
            statut='bloque'
        ).count(),
        'desactives': Utilisateur.objects.filter(
            pharmacie_active=pharmacie_active, 
            statut='desactive'
        ).count(),
    }
    
    return JsonResponse(stats)


# ==================== DASHBOARD ====================

@login_required
def dashboard(request):
    """
    Tableau de bord principal
    """
    pharmacie_active = request.user.pharmacie_active
    
    if not pharmacie_active:
        # L'utilisateur n'a pas de pharmacie active, le rediriger
        pharmacies_disponibles = Pharmacie.objects.filter(
            Q(proprietaire=request.user) | 
            Q(utilisateurs_actifs=request.user)
        ).distinct()
        
        if pharmacies_disponibles.count() == 1:
            # Une seule pharmacie, la définir automatiquement
            request.user.pharmacie_active = pharmacies_disponibles.first()
            request.user.save()
            return redirect('gestion_compte:dashboard')
        else:
            # Plusieurs pharmacies ou aucune, afficher la liste
            messages.info(request, "Veuillez sélectionner une pharmacie.")
            return redirect('gestion_compte:pharmacie_liste')
    
    # Statistiques générales
    stats = {
        'pharmacie': {
            'nom': pharmacie_active.nom_commercial,
            'code': pharmacie_active.code,
            'completion': pharmacie_active.pourcentage_completion,
        },
        'utilisateurs': {
            'total': Utilisateur.objects.filter(pharmacie_active=pharmacie_active).count(),
            'actifs': Utilisateur.objects.filter(
                pharmacie_active=pharmacie_active, 
                statut='actif'
            ).count(),
        }
    }
    
    context = {
        'stats': stats,
        'pharmacie_active': pharmacie_active,
        'est_proprietaire': pharmacie_active.proprietaire == request.user,
    }
    
    return render(request, 'gestion_compte/dashboard.html', context)




def dashboard(request):
    return render(request,'gestion_compte/dashboard.html')


def analyse(request):
    return render(request,'gestion_compte/analyse.html')


def parametre_compte(request):
    return render(request,'gestion_compte/parametre_compte.html')


def voir_profile(request):
    return render(request,'gestion_compte/voir_profile.html')

def centre_confidentialite(request):
    return render(request,'gestion_compte/centre_confidentialite.html')



