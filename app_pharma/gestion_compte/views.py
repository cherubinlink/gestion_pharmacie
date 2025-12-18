from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from django.http import JsonResponse
from django.contrib.auth.forms import PasswordChangeForm
from django.http import HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.db import transaction
import json
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

# Create your views here.
# ==========inscription ==========
def inscription_view(request):
    """Vue d'inscription"""
    if request.user.is_authenticated:
        return redirect('gestion_compte:dashboard')
    
    if request.method == 'POST':
        form = InscriptionForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Compte créé avec succès ! Bienvenue.')
            return redirect('gestion_compte:parametre_compte')
    else:
        form = InscriptionForm()
    
    context = {
        'form': form
    }
    return render(request, 'gestion_compte/inscription.html', context)


# connexion
def connexion_view(request):
    """Vue de connexion"""
    if request.user.is_authenticated:
        return redirect('gestion_compte:dashboard')
    
    if request.method == 'POST':
        form = ConnexionForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            
            # Vérifier si l'utilisateur peut se connecter
            if not user.peut_se_connecter():
                messages.error(request, f'Compte {user.get_statut_display()}. Contactez l\'administrateur.')
                return redirect('gestion_compte:connexion')
            
            # Enregistrer l'historique de connexion
            HistoriqueConnexion.objects.create(
                utilisateur=user,
                pharmacie=user.pharmacie_active,
                ip_address=request.META.get('REMOTE_ADDR', '0.0.0.0'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                succes=True
            )
            
            # Connexion
            login(request, user)
            user.date_derniere_connexion = timezone.now()
            user.ip_derniere_connexion = request.META.get('REMOTE_ADDR')
            user.reinitialiser_tentatives_connexion()
            user.save()
            
            messages.success(request, f'Bienvenue {user.get_full_name()} !')
            return redirect('gestion_compte:dashboard')
        else:
            messages.error(request, 'Email ou mot de passe incorrect.')
    else:
        form = ConnexionForm()
    context = {
        'form': form
    }
    return render(request, 'gestion_compte/connexion.html',context )


# ====== deconnexion =======
@login_required
def deconnexion_view(request):
    """Vue de déconnexion"""
    logout(request)
    messages.info(request, 'Vous avez été déconnecté.')
    return redirect('gestion_compte:connexion')



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



