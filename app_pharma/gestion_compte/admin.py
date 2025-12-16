from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count
from django.contrib.admin import SimpleListFilter
from django.utils.safestring import mark_safe
from gestion_compte.models import (
    Utilisateur, Pharmacie, Role, PermissionSysteme, RolePermission,
    MembrePharmacie, HistoriqueConnexion, HistoriqueModificationPharmacie,ProfilUtilisateur
)

# Register your models here.

"""
Administration Django pour ERP Pharmacie Multi-établissement
Application 1: Gestion des comptes & pharmacies
"""

# ==================== CONFIGURATION ADMIN SITE ====================

admin.site.site_header = "Administration ERP Pharmacie"
admin.site.site_title = "ERP Pharmacie"
admin.site.index_title = "Tableau de bord d'administration"


# ==================== FILTRES PERSONNALISÉS ====================

class PharmacieActiveFilter(admin.SimpleListFilter):
    """Filtre pour les utilisateurs avec/sans pharmacie active"""
    title = 'Pharmacie active'
    parameter_name = 'pharmacie_active'
    
    def lookups(self, request, model_admin):
        return (
            ('oui', 'Avec pharmacie active'),
            ('non', 'Sans pharmacie active'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'oui':
            return queryset.filter(pharmacie_active__isnull=False)
        if self.value() == 'non':
            return queryset.filter(pharmacie_active__isnull=True)


class ConfigurationCompleteFilter(admin.SimpleListFilter):
    """Filtre pour les pharmacies selon leur complétion"""
    title = 'Configuration'
    parameter_name = 'configuration'
    
    def lookups(self, request, model_admin):
        return (
            ('complete', 'Complète (100%)'),
            ('incomplete', 'Incomplète (<100%)'),
            ('faible', 'Faible (<50%)'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'complete':
            return queryset.filter(pourcentage_completion=100)
        if self.value() == 'incomplete':
            return queryset.filter(pourcentage_completion__lt=100)
        if self.value() == 'faible':
            return queryset.filter(pourcentage_completion__lt=50)


# ==================== INLINES ====================

class MembrePharmacieInline(admin.TabularInline):
    """Inline pour afficher les membres d'une pharmacie"""
    model = MembrePharmacie
    extra = 0
    fields = ('utilisateur', 'role', 'statut', 'date_ajout')
    readonly_fields = ('date_ajout',)
    autocomplete_fields = ['utilisateur']
    

class PharmaciesInline(admin.TabularInline):
    """Inline pour afficher les pharmacies d'un utilisateur"""
    model = MembrePharmacie
    fk_name = 'utilisateur'
    extra = 0
    fields = ('pharmacie', 'role', 'statut', 'date_ajout')
    readonly_fields = ('date_ajout',)
    verbose_name = "Pharmacie associée"
    verbose_name_plural = "Pharmacies associées"

class RolePermissionInline(admin.TabularInline):
    """Inline pour gérer les permissions d'un rôle"""
    model = RolePermission
    extra = 1
    autocomplete_fields = ['permission']


class PharmacieActiveFilter(SimpleListFilter):
    title = "Pharmacie active"
    parameter_name = "pharmacie_active_id"  # ⚠️ IMPORTANT

    def lookups(self, request, model_admin):
        return [
            (str(ph.id), ph.nom_commercial)
            for ph in Pharmacie.objects.all()
        ]

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(pharmacie_active_id=value)
        return queryset

class ProfilUtilisateurInline(admin.StackedInline):
    """Inline pour afficher le profil dans l'admin utilisateur"""
    model = ProfilUtilisateur
    can_delete = False
    verbose_name_plural = 'Profil utilisateur'
    fk_name = 'utilisateur'
    
    fieldsets = (
        ('Informations personnelles', {
            'fields': ('genre', 'situation_matrimoniale', 'nationalite', 'lieu_naissance')
        }),
        ('Documents d\'identité', {
            'fields': ('numero_cni', 'photo_cni_recto', 'photo_cni_verso'),
            'classes': ('collapse',)
        }),
        ('Informations professionnelles', {
            'fields': ('profession', 'diplome', 'specialite', 'numero_ordre', 'annees_experience')
        }),
        ('Contact d\'urgence', {
            'fields': ('contact_urgence_nom', 'contact_urgence_telephone', 'contact_urgence_relation'),
            'classes': ('collapse',)
        }),
        ('Préférences', {
            'fields': ('theme', 'langue', 'notifications_email', 'notifications_sms', 'notifications_push')
        }),
        ('Informations bancaires', {
            'fields': ('nom_banque', 'numero_compte', 'iban'),
            'classes': ('collapse',)
        }),
        ('Réseaux sociaux', {
            'fields': ('facebook', 'linkedin', 'twitter'),
            'classes': ('collapse',)
        }),
        ('Biographie et notes', {
            'fields': ('biographie', 'notes_internes'),
            'classes': ('collapse',)
        }),
        ('Statistiques', {
            'fields': ('score_points', 'niveau', 'badge', 'profil_complet', 'pourcentage_completion'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('profil_complet', 'pourcentage_completion')


# ==================== ADMIN UTILISATEUR ====================

@admin.register(Utilisateur)
class UtilisateurAdmin(BaseUserAdmin):
    """Administration du modèle Utilisateur"""
    
    list_display = (
        'email', 'get_full_name_display', 'telephone', 'statut_badge',
        'pharmacie_active', 'nb_pharmacies', 'derniere_connexion_display', 'date_creation'
    )
    list_filter = (
        'statut', 'is_active', 'is_staff', 'otp_actif',
        PharmacieActiveFilter, 'date_creation'
    )
    search_fields = ('email', 'first_name', 'last_name', 'telephone', 'username')
    ordering = ('-date_creation',)
    
    fieldsets = (
        ('Informations de connexion', {
            'fields': ('email', 'username', 'password')
        }),
        ('Informations personnelles', {
            'fields': (
                'first_name', 'last_name', 'photo', 'date_naissance',
                'telephone', 'whatsapp'
            )
        }),
        ('Adresse', {
            'fields': ('adresse', 'ville', 'pays'),
            'classes': ('collapse',)
        }),
        ('Statut et sécurité', {
            'fields': (
                'statut', 'raison_statut', 'date_changement_statut',
                'is_active', 'is_staff', 'is_superuser'
            )
        }),
        ('Pharmacie', {
            'fields': ('pharmacie_active',)
        }),
        ('Sécurité avancée', {
            'fields': (
                'otp_actif', 'tentatives_connexion', 'derniere_tentative',
                'date_derniere_connexion', 'ip_derniere_connexion'
            ),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('date_creation', 'date_modification', 'cree_par'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = (
        'date_creation', 'date_modification', 'date_derniere_connexion',
        'ip_derniere_connexion', 'tentatives_connexion', 'derniere_tentative'
    )
    
    inlines = [ProfilUtilisateurInline,PharmaciesInline]
    
    def get_full_name_display(self, obj):
        return obj.get_full_name()
    get_full_name_display.short_description = "Nom complet"
    
    def statut_badge(self, obj):
        """Affiche un badge coloré pour le statut"""
        colors = {
            'actif': 'success',
            'suspendu': 'warning',
            'bloque': 'danger',
            'desactive': 'secondary'
        }
        color = colors.get(obj.statut, 'secondary')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            f'var(--bs-{color})',
            obj.get_statut_display()
        )
    statut_badge.short_description = "Statut"
    
    def nb_pharmacies(self, obj):
        """Nombre de pharmacies associées"""
        count = obj.pharmacies.filter(statut='actif').count()
        return format_html(
            '<span style="font-weight: bold; color: #007bff;">{}</span>',
            count
        )
    nb_pharmacies.short_description = "Pharmacies"
    
    def profil_completion(self, obj):
        """Affiche le pourcentage de complétion du profil"""
        if hasattr(obj, 'profil'):
            pct = obj.profil.pourcentage_completion
            if pct >= 80:
                color = '#28a745'  # Vert
            elif pct >= 50:
                color = '#ffc107'  # Jaune
            else:
                color = '#dc3545'  # Rouge
            
            return format_html(
                '<div style="width: 100px; background-color: #e9ecef; border-radius: 3px; overflow: hidden;">'
                '<div style="width: {}%; background-color: {}; color: white; text-align: center; '
                'padding: 2px 0; font-size: 10px; font-weight: bold;">{} %</div>'
                '</div>',
                pct, color, pct
            )
        return mark_safe('<span style="color: gray;">N/A</span>')
    profil_completion.short_description = "Profil"
    
    def derniere_connexion_display(self, obj):
        if obj.date_derniere_connexion:
            delta = timezone.now() - obj.date_derniere_connexion
            if delta.days == 0:
                return mark_safe('<span style="color: green;">Aujourd\'hui</span>')
            elif delta.days == 1:
                return mark_safe('<span style="color: orange;">Hier</span>')
            elif delta.days < 7:
                return format_html(
                    '<span style="color: orange;">Il y a {} jours</span>',
                    delta.days
                )
            else:
                return format_html(
                    '<span style="color: red;">Il y a {} jours</span>',
                    delta.days
                )
        return mark_safe('<span style="color: gray;">Jamais</span>')
    derniere_connexion_display.short_description = "Dernière connexion"
    
    actions = ['activer_utilisateurs', 'suspendre_utilisateurs', 'reinitialiser_tentatives']
    
    def activer_utilisateurs(self, request, queryset):
        """Action pour activer des utilisateurs"""
        count = queryset.update(statut='actif', raison_statut='')
        self.message_user(request, f"{count} utilisateur(s) activé(s) avec succès.")
    activer_utilisateurs.short_description = "Activer les utilisateurs sélectionnés"
    
    def suspendre_utilisateurs(self, request, queryset):
        """Action pour suspendre des utilisateurs"""
        count = queryset.update(
            statut='suspendu',
            raison_statut='Suspendu par l\'administrateur',
            date_changement_statut=timezone.now()
        )
        self.message_user(request, f"{count} utilisateur(s) suspendu(s).")
    suspendre_utilisateurs.short_description = "Suspendre les utilisateurs sélectionnés"
    
    def reinitialiser_tentatives(self, request, queryset):
        """Action pour réinitialiser les tentatives de connexion"""
        count = queryset.update(tentatives_connexion=0)
        self.message_user(request, f"Tentatives réinitialisées pour {count} utilisateur(s).")
    reinitialiser_tentatives.short_description = "Réinitialiser les tentatives de connexion"
    
    
# ==================== ADMIN PHARMACIE ====================

@admin.register(Pharmacie)
class PharmacieAdmin(admin.ModelAdmin):
    """Administration du modèle Pharmacie"""
    
    list_display = (
        'code', 'nom_commercial', 'ville', 'proprietaire',
        'statut_badge', 'completion_progress', 'nb_membres', 'date_creation'
    )
    list_filter = ('statut', ConfigurationCompleteFilter, 'pays', 'ville', 'date_creation')
    search_fields = ('code', 'nom_commercial', 'numero_autorisation', 'nif', 'rccm', 'ville')
    ordering = ('-date_creation',)
    
    fieldsets = (
        ('Identité', {
            'fields': ('code', 'nom_commercial', 'slogan', 'logo')
        }),
        ('Localisation', {
            'fields': (
                'adresse', 'ville', 'region', 'pays', 'code_postal',
                ('latitude', 'longitude')
            )
        }),
        ('Contact', {
            'fields': (
                'telephone_principal', 'telephone_secondaire',
                'email', 'whatsapp', 'site_web'
            )
        }),
        ('Informations légales', {
            'fields': (
                'numero_autorisation', 'nif', 'rccm',
                'date_autorisation', 'date_expiration_autorisation'
            )
        }),
        ('Paramètres opérationnels', {
            'fields': (
                ('devise', 'symbole_devise'), 'taux_tva',
                'fuseau_horaire', 'horaires_ouverture'
            )
        }),
        ('Gestion', {
            'fields': (
                'proprietaire', 'statut',
                'pourcentage_completion', 'configuration_complete'
            )
        }),
        ('Métadonnées', {
            'fields': ('date_creation', 'date_modification'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = (
        'code', 'pourcentage_completion', 'configuration_complete',
        'date_creation', 'date_modification'
    )
    
    inlines = [MembrePharmacieInline]
    
    autocomplete_fields = ['proprietaire']
    
    def statut_badge(self, obj):
        """Badge coloré pour le statut"""
        colors = {
            'active': 'success',
            'suspendue': 'warning',
            'fermee': 'danger'
        }
        color = colors.get(obj.statut, 'secondary')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            f'var(--bs-{color})',
            obj.get_statut_display()
        )
    statut_badge.short_description = "Statut"
    
    def completion_progress(self, obj):
        """Barre de progression de la complétion"""
        percentage = obj.pourcentage_completion
        if percentage == 100:
            color = '#28a745'
        elif percentage >= 70:
            color = '#ffc107'
        else:
            color = '#dc3545'
        
        return format_html(
            '<div style="width: 100px; background-color: #e9ecef; border-radius: 3px; overflow: hidden;">'
            '<div style="width: {}%; background-color: {}; color: white; text-align: center; '
            'padding: 2px; font-size: 11px; font-weight: bold;">{:.0f}%</div>'
            '</div>',
            percentage, color, percentage
        )
    completion_progress.short_description = "Complétion"
    
    def nb_membres(self, obj):
        """Nombre de membres actifs"""
        count = obj.membres.filter(statut='actif').count()
        return format_html('<strong>{}</strong>', count)
    nb_membres.short_description = "Membres"
    
    actions = ['activer_pharmacies', 'suspendre_pharmacies', 'recalculer_completion']
    
    def activer_pharmacies(self, request, queryset):
        count = queryset.update(statut='active')
        self.message_user(request, f"{count} pharmacie(s) activée(s).")
    activer_pharmacies.short_description = "Activer les pharmacies sélectionnées"
    
    def suspendre_pharmacies(self, request, queryset):
        count = queryset.update(statut='suspendue')
        self.message_user(request, f"{count} pharmacie(s) suspendue(s).")
    suspendre_pharmacies.short_description = "Suspendre les pharmacies sélectionnées"
    
    def recalculer_completion(self, request, queryset):
        for pharmacie in queryset:
            pharmacie.save()  # Déclenche le recalcul
        self.message_user(request, "Complétion recalculée pour toutes les pharmacies sélectionnées.")
    recalculer_completion.short_description = "Recalculer le pourcentage de complétion"


# ==================== ADMIN RÔLES ET PERMISSIONS ====================

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """Administration des rôles"""
    
    list_display = ('nom', 'code', 'est_role_systeme', 'nb_permissions', 'nb_utilisateurs', 'date_creation')
    list_filter = ('est_role_systeme', 'date_creation')
    search_fields = ('nom', 'code', 'description')
    ordering = ('nom',)
    
    fieldsets = (
        (None, {
            'fields': ('nom', 'code', 'description', 'est_role_systeme')
        }),
        ('Métadonnées', {
            'fields': ('date_creation', 'date_modification'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('date_creation', 'date_modification')
    inlines = [RolePermissionInline]
    
    def nb_permissions(self, obj):
        count = obj.permissions.count()
        return format_html('<span style="color: #007bff; font-weight: bold;">{}</span>', count)
    nb_permissions.short_description = "Permissions"
    
    def nb_utilisateurs(self, obj):
        count = MembrePharmacie.objects.filter(role=obj, statut='actif').count()
        return format_html('<span style="color: #28a745; font-weight: bold;">{}</span>', count)
    nb_utilisateurs.short_description = "Utilisateurs"


@admin.register(PermissionSysteme)
class PermissionSystemeAdmin(admin.ModelAdmin):
    """Administration des permissions"""
    
    list_display = ('code', 'nom', 'module', 'nb_roles')
    list_filter = ('module',)
    search_fields = ('code', 'nom', 'module', 'description')
    ordering = ('module', 'nom')
    
    fieldsets = (
        (None, {
            'fields': ('code', 'nom', 'module', 'description')
        }),
    )
    
    def nb_roles(self, obj):
        count = RolePermission.objects.filter(permission=obj).count()
        return format_html('<span style="color: #007bff;">{}</span>', count)
    nb_roles.short_description = "Rôles"
    
@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    """Administration des liaisons rôle-permission"""
    
    list_display = ('role', 'permission', 'module_permission')
    list_filter = ('role', 'permission__module')
    search_fields = ('role__nom', 'permission__nom')
    autocomplete_fields = ['role', 'permission']
    
    def module_permission(self, obj):
        return obj.permission.module
    module_permission.short_description = "Module"
    

# ==================== ADMIN MEMBRE PHARMACIE ====================

@admin.register(MembrePharmacie)
class MembrePharmacieAdmin(admin.ModelAdmin):
    """Administration des membres de pharmacie"""
    
    list_display = (
        'utilisateur', 'pharmacie', 'role', 'statut_badge',
        'date_ajout', 'ajoute_par'
    )
    list_filter = ('statut', 'role', 'date_ajout')
    search_fields = (
        'utilisateur__email', 'utilisateur__first_name', 'utilisateur__last_name',
        'pharmacie__nom_commercial', 'pharmacie__code'
    )
    ordering = ('-date_ajout',)
    
    fieldsets = (
        (None, {
            'fields': ('utilisateur', 'pharmacie', 'role')
        }),
        ('Statut', {
            'fields': ('statut', 'date_ajout', 'date_retrait', 'ajoute_par')
        }),
    )
    
    readonly_fields = ('date_ajout',)
    autocomplete_fields = ['utilisateur', 'pharmacie', 'ajoute_par']
    
    def statut_badge(self, obj):
        colors = {
            'actif': 'success',
            'inactif': 'secondary',
            'invite': 'info'
        }
        color = colors.get(obj.statut, 'secondary')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            f'var(--bs-{color})',
            obj.get_statut_display()
        )
    statut_badge.short_description = "Statut"
    
# ==================== ADMIN HISTORIQUES ====================

@admin.register(HistoriqueConnexion)
class HistoriqueConnexionAdmin(admin.ModelAdmin):
    """Administration de l'historique des connexions"""
    
    list_display = (
        'utilisateur', 'pharmacie', 'date_connexion',
        'ip_address', 'navigateur', 'succes_badge'
    )
    list_filter = ('succes', 'date_connexion', 'navigateur', 'systeme_exploitation')
    search_fields = (
        'utilisateur__email', 'ip_address',
        'pharmacie__nom_commercial'
    )
    ordering = ('-date_connexion',)
    date_hierarchy = 'date_connexion'
    
    fieldsets = (
        ('Utilisateur', {
            'fields': ('utilisateur', 'pharmacie', 'date_connexion')
        }),
        ('Informations techniques', {
            'fields': (
                'ip_address', 'user_agent', 'navigateur',
                'systeme_exploitation', 'appareil'
            )
        }),
        ('Résultat', {
            'fields': ('succes', 'raison_echec')
        }),
    )
    
    readonly_fields = ('date_connexion',)
    
    def succes_badge(self, obj):
        if obj.succes:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Succès</span>'
            )
        return format_html(
            '<span style="color: red; font-weight: bold;">✗ Échec</span>'
        )
    succes_badge.short_description = "Résultat"
    
    def has_add_permission(self, request):
        """Empêcher l'ajout manuel"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Lecture seule"""
        return False


@admin.register(HistoriqueModificationPharmacie)
class HistoriqueModificationPharmacieAdmin(admin.ModelAdmin):
    """Administration de l'historique des modifications"""
    
    list_display = (
        'pharmacie', 'champ_modifie', 'utilisateur',
        'date_modification', 'ip_address'
    )
    list_filter = ('champ_modifie', 'date_modification')
    search_fields = (
        'pharmacie__nom_commercial', 'pharmacie__code',
        'utilisateur__email', 'champ_modifie'
    )
    ordering = ('-date_modification',)
    date_hierarchy = 'date_modification'
    
    fieldsets = (
        ('Contexte', {
            'fields': ('pharmacie', 'utilisateur', 'date_modification', 'ip_address')
        }),
        ('Modification', {
            'fields': ('champ_modifie', 'ancienne_valeur', 'nouvelle_valeur')
        }),
    )
    
    readonly_fields = ('date_modification',)
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

@admin.register(ProfilUtilisateur)
class ProfilUtilisateurAdmin(admin.ModelAdmin):
    """Administration du profil utilisateur (vue séparée)"""
    
    list_display = (
        'utilisateur', 'genre', 'profession', 'numero_ordre',
        'pourcentage_completion', 'profil_complet', 'date_creation'
    )
    
    list_filter = ('genre', 'profil_complet', 'theme', 'langue', 'date_creation')
    search_fields = ('utilisateur__email', 'utilisateur__first_name', 'utilisateur__last_name', 'profession', 'numero_ordre')
    
    readonly_fields = ('profil_complet', 'pourcentage_completion', 'date_creation', 'date_modification')
    
    fieldsets = (
        ('Utilisateur', {
            'fields': ('utilisateur',)
        }),
        ('Informations personnelles', {
            'fields': ('genre', 'situation_matrimoniale', 'nationalite', 'lieu_naissance')
        }),
        ('Documents', {
            'fields': ('numero_cni', 'photo_cni_recto', 'photo_cni_verso')
        }),
        ('Professionnel', {
            'fields': ('profession', 'diplome', 'specialite', 'numero_ordre', 'annees_experience')
        }),
        ('Contact d\'urgence', {
            'fields': ('contact_urgence_nom', 'contact_urgence_telephone', 'contact_urgence_relation')
        }),
        ('Préférences', {
            'fields': ('theme', 'langue', 'notifications_email', 'notifications_sms', 'notifications_push')
        }),
        ('Informations bancaires', {
            'fields': ('nom_banque', 'numero_compte', 'iban')
        }),
        ('Réseaux sociaux', {
            'fields': ('facebook', 'linkedin', 'twitter')
        }),
        ('Biographie', {
            'fields': ('biographie', 'notes_internes')
        }),
        ('Gamification', {
            'fields': ('score_points', 'niveau', 'badge')
        }),
        ('Métadonnées', {
            'fields': ('profil_complet', 'pourcentage_completion', 'date_creation', 'date_modification')
        }),
    )

