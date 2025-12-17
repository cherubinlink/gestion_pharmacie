from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from django.http import JsonResponse
from django.contrib.auth.forms import PasswordChangeForm
from gestion_compte.models import (
    Utilisateur,UtilisateurManager,Pharmacie,ProfilUtilisateur,
    Role, PermissionSysteme, RolePermission, MembrePharmacie,
    HistoriqueConnexion, HistoriqueModificationPharmacie
)
from gestion_compte.forms import (
    InscriptionForm, ConnexionForm, ProfilUtilisateurForm, PharmacieForm,
    UtilisateurForm, InvitationMembreForm, PreferencesUtilisateurForm, 
) 

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



# ==================== TABLEAU DE BORD ====================

@login_required
def tableau_bord_view(request):
    """Tableau de bord principal"""
    user = request.user
    
    context = {
        'pharmacie_active': user.pharmacie_active,
        'profil': user.profil,
        'nb_pharmacies': user.pharmacies.filter(statut='actif').count(),
        'historique_connexions': user.connexions.all()[:5],
    }
    
    return render(request, 'gestion_compte/dashboard.html', context)


def _get_base_context(request):
    """Fonction helper pour générer le contexte de base"""
    user = request.user
    profil = user.profil
    pharmacie = user.pharmacie_active
    
    # Récupérer les membres si pharmacie existe
    membres = []
    if pharmacie:
        membres = pharmacie.membres.select_related('utilisateur', 'role').all()
    
    # Statistiques
    nb_employes = membres.count() if membres else 0
    nb_clients = 0  # À implémenter
    nb_ventes_mois = 0  # À implémenter
    
    return {
        'user': user,
        'profil': profil,
        'pharmacie': pharmacie,
        'membres': membres,
        'pharmacies_user': user.pharmacies.select_related('pharmacie', 'role').all(),
        'nb_employes': nb_employes,
        'nb_clients': nb_clients,
        'nb_ventes_mois': nb_ventes_mois,
        'historique_connexions': user.connexions.all()[:5],
    }


# ==================== VUE PRINCIPALE (LECTURE SEULE) ====================
@login_required
def parametres_compte_view(request):
    """
    Vue principale - Affichage en lecture seule (Onglet 1)
    """
    context = _get_base_context(request)
    context['tab_active'] = 'profile-1'
    
    # Initialiser tous les formulaires vides pour l'affichage
    context['profil_form'] = ProfilUtilisateurForm(instance=context['profil'])
    context['user_form'] = UtilisateurForm(instance=request.user)
    context['pharmacie_form'] = PharmacieForm(instance=context['pharmacie']) if context['pharmacie'] else None
    context['invitation_form'] = InvitationMembreForm()
    context['preferences_form'] = PreferencesUtilisateurForm(instance=context['profil'])
    
    return render(request, 'gestion_compte/parametre_compte.html', context)

# ==================== ONGLET 2: PROFIL PERSONNEL ====================
@login_required
def modifier_profil_personnel_view(request):
    """
    Modification du profil personnel (Onglet 2)
    """
    context = _get_base_context(request)
    context['tab_active'] = 'profile-2'
    
    profil = context['profil']
    user = request.user
    
    if request.method == 'POST':
        profil_form = ProfilUtilisateurForm(request.POST, request.FILES, instance=profil)
        user_form = UtilisateurForm(request.POST, request.FILES, instance=user)
        
        if profil_form.is_valid() and user_form.is_valid():
            profil_form.save()
            user_form.save()
            messages.success(request, '✅ Profil mis à jour avec succès !')
            return redirect('gestion_compte:modifier_profil_personnel')
        else:
            messages.error(request, '❌ Erreur lors de la mise à jour du profil.')
    else:
        profil_form = ProfilUtilisateurForm(instance=profil)
        user_form = UtilisateurForm(instance=user)
    
    # Ajouter les formulaires au contexte
    context['profil_form'] = profil_form
    context['user_form'] = user_form
    context['pharmacie_form'] = PharmacieForm(instance=context['pharmacie']) if context['pharmacie'] else None
    context['invitation_form'] = InvitationMembreForm()
    context['preferences_form'] = PreferencesUtilisateurForm(instance=profil)
    
    return render(request, 'gestion_compte/parametre_compte.html', context)

# ==================== ONGLET 3: CONFIGURATION PHARMACIE ====================
@login_required
def configuration_pharmacie_view(request):
    """
    Configuration de la pharmacie (Onglet 3)
    """
    context = _get_base_context(request)
    context['tab_active'] = 'profile-3'
    
    pharmacie = context['pharmacie']
    
    if not pharmacie:
        messages.warning(request, '⚠️ Aucune pharmacie active.')
        context['pharmacie_form'] = None
    else:
        if request.method == 'POST':
            pharmacie_form = PharmacieForm(request.POST, request.FILES, instance=pharmacie)
            
            if pharmacie_form.is_valid():
                pharmacie_form.save()
                messages.success(request, '✅ Configuration de la pharmacie mise à jour !')
                return redirect('gestion_compte:configuration_pharmacie')
            else:
                messages.error(request, '❌ Erreur lors de la mise à jour.')
        else:
            pharmacie_form = PharmacieForm(instance=pharmacie)
        
        context['pharmacie_form'] = pharmacie_form
    
    # Autres formulaires pour l'affichage
    context['profil_form'] = ProfilUtilisateurForm(instance=context['profil'])
    context['user_form'] = UtilisateurForm(instance=request.user)
    context['invitation_form'] = InvitationMembreForm()
    context['preferences_form'] = PreferencesUtilisateurForm(instance=context['profil'])
    
    return render(request, 'gestion_compte/parametre_compte.html', context)

# ==================== ONGLET 4: PLANNING (À IMPLÉMENTER) ====================
@login_required
def planning_view(request):
    """
    Gestion du planning (Onglet 4)
    """
    context = _get_base_context(request)
    context['tab_active'] = 'profile-4'
    
    # TODO: Implémenter la logique du planning
    
    # Formulaires pour l'affichage
    context['profil_form'] = ProfilUtilisateurForm(instance=context['profil'])
    context['user_form'] = UtilisateurForm(instance=request.user)
    context['pharmacie_form'] = PharmacieForm(instance=context['pharmacie']) if context['pharmacie'] else None
    context['invitation_form'] = InvitationMembreForm()
    context['preferences_form'] = PreferencesUtilisateurForm(instance=context['profil'])
    
    return render(request, 'gestion_compte/parametre_compte.html', context)

# ==================== ONGLET 5: GESTION DES MEMBRES ====================
@login_required
def gestion_membres_view(request):
    """
    Gestion des membres de la pharmacie (Onglet 5)
    """
    context = _get_base_context(request)
    context['tab_active'] = 'profile-5'
    
    pharmacie = context['pharmacie']
    
    if not pharmacie:
        messages.warning(request, '⚠️ Aucune pharmacie active.')
    else:
        if request.method == 'POST':
            invitation_form = InvitationMembreForm(request.POST)
            
            if invitation_form.is_valid():
                email = invitation_form.cleaned_data['email']
                role = invitation_form.cleaned_data['role']
                
                # TODO: Implémenter l'envoi d'invitation par email
                # Créer une invitation en base de données
                
                messages.success(request, f'✅ Invitation envoyée à {email}')
                return redirect('gestion_compte:gestion_membres')
            else:
                messages.error(request, '❌ Erreur dans le formulaire.')
        else:
            invitation_form = InvitationMembreForm()
        
        context['invitation_form'] = invitation_form
    
    # Autres formulaires pour l'affichage
    context['profil_form'] = ProfilUtilisateurForm(instance=context['profil'])
    context['user_form'] = UtilisateurForm(instance=request.user)
    context['pharmacie_form'] = PharmacieForm(instance=context['pharmacie']) if context['pharmacie'] else None
    context['preferences_form'] = PreferencesUtilisateurForm(instance=context['profil'])
    
    return render(request, 'gestion_compte/parametre_compte.html', context)


# ==================== ONGLET 6: PRÉFÉRENCES ====================

@login_required
def preferences_view(request):
    """
    Préférences utilisateur (Onglet 6)
    """
    context = _get_base_context(request)
    context['tab_active'] = 'profile-6'
    
    profil = context['profil']
    
    if request.method == 'POST':
        preferences_form = PreferencesUtilisateurForm(request.POST, instance=profil)
        
        if preferences_form.is_valid():
            preferences_form.save()
            messages.success(request, '✅ Préférences mises à jour !')
            return redirect('gestion_compte:preferences')
        else:
            messages.error(request, '❌ Erreur lors de la mise à jour.')
    else:
        preferences_form = PreferencesUtilisateurForm(instance=profil)
    
    context['preferences_form'] = preferences_form
    
    # Autres formulaires pour l'affichage
    context['profil_form'] = ProfilUtilisateurForm(instance=profil)
    context['user_form'] = UtilisateurForm(instance=request.user)
    context['pharmacie_form'] = PharmacieForm(instance=context['pharmacie']) if context['pharmacie'] else None
    context['invitation_form'] = InvitationMembreForm()
    
    return render(request, 'gestion_compte/parametre_compte.html', context)


# ==================== ACTIONS COMPLÉMENTAIRES ====================

@login_required
def changer_pharmacie_active_view(request, pharmacie_id):
    """Changer la pharmacie active"""
    membre = get_object_or_404(
        MembrePharmacie,
        utilisateur=request.user,
        pharmacie_id=pharmacie_id,
        statut='actif'
    )
    
    request.user.pharmacie_active = membre.pharmacie
    request.user.save()
    
    messages.success(request, f'✅ Pharmacie active changée : {membre.pharmacie.nom_commercial}')
    return redirect('gestion_compte:parametre_compte')


@login_required
def retirer_membre_view(request, membre_id):
    """Retirer un membre de la pharmacie"""
    pharmacie = request.user.pharmacie_active
    
    if not pharmacie:
        messages.error(request, '❌ Aucune pharmacie active.')
        return redirect('gestion_compte:gestion_membres')
    
    membre = get_object_or_404(
        MembrePharmacie,
        id=membre_id,
        pharmacie=pharmacie
    )
    
    # Vérifier les permissions
    if request.user == pharmacie.proprietaire or request.user.is_staff:
        membre.statut = 'inactif'
        membre.date_retrait = timezone.now()
        membre.save()
        
        messages.success(request, f'✅ {membre.utilisateur.get_full_name()} retiré avec succès')
    else:
        messages.error(request, '❌ Permission refusée.')
    
    return redirect('gestion_compte:gestion_membres')







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



