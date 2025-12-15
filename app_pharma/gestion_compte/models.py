
"""
Models Django pour ERP Pharmacie Multi-établissement
Application 1: Gestion des comptes & pharmacies
"""


from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator,MinValueValidator,MaxValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import uuid

# Create your models here.



# ==================== MANAGER PERSONNALISÉ ====================

class UtilisateurManager(BaseUserManager):
    """Manager personnalisé pour le modèle Utilisateur"""
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'adresse email est obligatoire")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Le superuser doit avoir is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Le superuser doit avoir is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)

# ==================== MODÈLES PRINCIPAUX ====================

class Utilisateur(AbstractUser):
    """
    Modèle utilisateur étendu pour gérer les comptes de l'ERP
    """
    
    STATUT_CHOICES = [
        ('actif', 'Actif'),
        ('suspendu', 'Suspendu'),
        ('bloque', 'Bloqué'),
        ('desactive', 'Désactivé'),
    ]
    
    # Champs de base
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True, blank=True, null=True)
    email = models.EmailField(unique=True, verbose_name="Email")
    telephone = models.CharField(
        max_length=20,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$')],
        blank=True,
        null=True
    )
    whatsapp = models.CharField(
        max_length=20,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$')],
        blank=True,
        null=True
    )
    
    # Informations personnelles
    photo = models.ImageField(upload_to='utilisateurs/photos/', blank=True, null=True)
    date_naissance = models.DateField(blank=True, null=True)
    adresse = models.TextField(blank=True)
    ville = models.CharField(max_length=100, blank=True)
    pays = models.CharField(max_length=100, default='Cameroun')
    
    # Gestion du statut
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='actif')
    raison_statut = models.TextField(blank=True, help_text="Raison de suspension/blocage")
    date_changement_statut = models.DateTimeField(blank=True, null=True)
    
    # Pharmacie active (pour les utilisateurs multi-pharmacies)
    pharmacie_active = models.ForeignKey(
        'gestion_compte.Pharmacie',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='utilisateurs_actifs'
    )
    
    # Sécurité
    otp_secret = models.CharField(max_length=32, blank=True)
    otp_actif = models.BooleanField(default=False)
    tentatives_connexion = models.IntegerField(default=0)
    derniere_tentative = models.DateTimeField(blank=True, null=True)
    date_derniere_connexion = models.DateTimeField(blank=True, null=True)
    ip_derniere_connexion = models.GenericIPAddressField(blank=True, null=True)
    
    # Métadonnées
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    cree_par = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='utilisateurs_crees'
    )
    
    objects = UtilisateurManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['statut']),
            models.Index(fields=['pharmacie_active']),
        ]
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email
    
    def peut_se_connecter(self):
        """Vérifie si l'utilisateur peut se connecter"""
        return self.statut == 'actif' and self.is_active
    
    def incrementer_tentatives_connexion(self):
        """Incrémente le compteur de tentatives de connexion"""
        self.tentatives_connexion += 1
        self.derniere_tentative = timezone.now()
        if self.tentatives_connexion >= 5:
            self.statut = 'bloque'
            self.raison_statut = "Trop de tentatives de connexion échouées"
        self.save()
    
    def reinitialiser_tentatives_connexion(self):
        """Réinitialise le compteur de tentatives"""
        self.tentatives_connexion = 0
        self.save()


class Pharmacie(models.Model):
    """
    Modèle représentant une pharmacie dans le système
    """
    
    STATUT_CHOICES = [
        ('active', 'Active'),
        ('suspendue', 'Suspendue'),
        ('fermee', 'Fermée'),
    ]
    
    # Identifiants
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, unique=True, editable=False)
    
    # Informations de base
    nom_commercial = models.CharField(max_length=200)
    slogan = models.CharField(max_length=255, blank=True)
    logo = models.ImageField(upload_to='pharmacies/logos/', blank=True, null=True)
    
    # Localisation
    adresse = models.TextField()
    ville = models.CharField(max_length=100)
    region = models.CharField(max_length=100, blank=True)
    pays = models.CharField(max_length=100, default='Cameroun')
    code_postal = models.CharField(max_length=20, blank=True)
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True,
        help_text="Coordonnée GPS latitude"
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True,
        help_text="Coordonnée GPS longitude"
    )
    
    # Contact
    telephone_principal = models.CharField(
        max_length=20,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$')]
    )
    telephone_secondaire = models.CharField(
        max_length=20,
        blank=True,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$')]
    )
    email = models.EmailField()
    whatsapp = models.CharField(
        max_length=20,
        blank=True,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$')]
    )
    site_web = models.URLField(blank=True,null= True)
    
    # Informations légales
    numero_autorisation = models.CharField(
        max_length=100,
        unique=True,
        help_text="Numéro d'autorisation d'exploitation"
    )
    nif = models.CharField(
        max_length=50,
        blank=True,
        help_text="Numéro d'Identification Fiscale"
    )
    rccm = models.CharField(
        max_length=50,
        blank=True,
        help_text="Registre de Commerce et du Crédit Mobilier"
    )
    date_autorisation = models.DateField(blank=True, null=True)
    date_expiration_autorisation = models.DateField(blank=True, null=True)
    
    # Paramètres opérationnels
    devise = models.CharField(max_length=10, default='XAF')
    symbole_devise = models.CharField(max_length=5, default='FCFA')
    taux_tva = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=19.25,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Taux de TVA en pourcentage"
    )
    fuseau_horaire = models.CharField(
        max_length=50,
        default='Africa/Douala',
        help_text="Fuseau horaire de la pharmacie"
    )
    
    # Horaires d'ouverture (format JSON ou TextField)
    horaires_ouverture = models.JSONField(
        default=dict,
        help_text="Format: {'lundi': {'ouvert': true, 'debut': '08:00', 'fin': '18:00'}, ...}"
    )
    
    # Propriétaire
    proprietaire = models.ForeignKey(
        Utilisateur,
        on_delete=models.PROTECT,
        related_name='pharmacies_possedees'
    )
    
    # Statut et configuration
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='active')
    configuration_complete = models.BooleanField(default=False)
    pourcentage_completion = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    
    # Métadonnées
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Pharmacie"
        verbose_name_plural = "Pharmacies"
        ordering = ['nom_commercial']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['proprietaire']),
            models.Index(fields=['statut']),
        ]
    
    def __str__(self):
        return f"{self.nom_commercial} ({self.code})"
    
    def save(self, *args, **kwargs):
        # Générer un code unique si nouveau
        if not self.code:
            self.code = self._generer_code_unique()
        
        # Calculer le pourcentage de complétion
        self.pourcentage_completion = self.calculer_completion()
        self.configuration_complete = self.pourcentage_completion == 100
        
        super().save(*args, **kwargs)
    
    def _generer_code_unique(self):
        """Génère un code unique pour la pharmacie"""
        import random
        import string
        prefix = 'PH'
        while True:
            code = f"{prefix}{random.randint(10000, 99999)}"
            if not Pharmacie.objects.filter(code=code).exists():
                return code
    
    def calculer_completion(self):
        """Calcule le pourcentage de complétion de la configuration"""
        champs_obligatoires = [
            self.nom_commercial, self.adresse, self.ville,
            self.telephone_principal, self.email, self.numero_autorisation
        ]
        champs_optionnels = [
            self.logo, self.slogan, self.latitude, self.longitude,
            self.nif, self.rccm, self.whatsapp, self.site_web
        ]
        
        obligatoires_remplis = sum(1 for champ in champs_obligatoires if champ)
        optionnels_remplis = sum(1 for champ in champs_optionnels if champ)
        
        # 70% pour les obligatoires, 30% pour les optionnels
        score_obligatoires = (obligatoires_remplis / len(champs_obligatoires)) * 70
        score_optionnels = (optionnels_remplis / len(champs_optionnels)) * 30
        
        return int(score_obligatoires + score_optionnels)


class Role(models.Model):
    """
    Modèle pour définir les rôles dans le système
    """
    
    ROLES_SYSTEME = [
        ('proprietaire', 'Propriétaire'),
        ('administrateur', 'Administrateur'),
        ('pharmacien', 'Pharmacien'),
        ('caissier', 'Caissier'),
        ('gestionnaire_stock', 'Gestionnaire de stock'),
        ('livreur', 'Livreur'),
        ('client', 'Client'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, choices=ROLES_SYSTEME, unique=True)
    description = models.TextField(blank=True)
    est_role_systeme = models.BooleanField(default=True, help_text="Rôle prédéfini du système")
    
    # Métadonnées
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Rôle"
        verbose_name_plural = "Rôles"
        ordering = ['nom']
    
    def __str__(self):
        return self.nom


class PermissionSysteme(models.Model):
    """
    Modèle pour définir les permissions granulaires
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=100, unique=True)
    nom = models.CharField(max_length=200)
    module = models.CharField(max_length=100, help_text="Module de l'ERP concerné")
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Permission"
        verbose_name_plural = "Permissions"
        ordering = ['module', 'nom']
    
    def __str__(self):
        return f"{self.module} - {self.nom}"


class RolePermission(models.Model):
    """
    Table de liaison entre Rôles et Permissions
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='permissions')
    permission = models.ForeignKey(PermissionSysteme, on_delete=models.CASCADE)
    
    class Meta:
        verbose_name = "Permission de rôle"
        verbose_name_plural = "Permissions de rôles"
        unique_together = ['role', 'permission']
    
    def __str__(self):
        return f"{self.role.nom} - {self.permission.nom}"


class MembrePharmacie(models.Model):
    """
    Table de liaison entre Utilisateurs et Pharmacies avec leur rôle
    """
    
    STATUT_CHOICES = [
        ('actif', 'Actif'),
        ('inactif', 'Inactif'),
        ('invite', 'Invité'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='pharmacies')
    pharmacie = models.ForeignKey(Pharmacie, on_delete=models.CASCADE, related_name='membres')
    role = models.ForeignKey(Role, on_delete=models.PROTECT)
    
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='actif')
    date_ajout = models.DateTimeField(auto_now_add=True)
    date_retrait = models.DateTimeField(blank=True, null=True)
    ajoute_par = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        related_name='membres_ajoutes'
    )
    
    class Meta:
        verbose_name = "Membre de pharmacie"
        verbose_name_plural = "Membres de pharmacie"
        unique_together = ['utilisateur', 'pharmacie']
        ordering = ['-date_ajout']
        indexes = [
            models.Index(fields=['utilisateur', 'pharmacie']),
            models.Index(fields=['pharmacie', 'statut']),
        ]
    
    def __str__(self):
        return f"{self.utilisateur.get_full_name()} - {self.pharmacie.nom_commercial} ({self.role.nom})"


class HistoriqueConnexion(models.Model):
    """
    Historique des connexions des utilisateurs
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='connexions')
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Pharmacie active lors de la connexion"
    )
    
    date_connexion = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    navigateur = models.CharField(max_length=100, blank=True)
    systeme_exploitation = models.CharField(max_length=100, blank=True)
    appareil = models.CharField(max_length=100, blank=True)
    succes = models.BooleanField(default=True)
    raison_echec = models.CharField(max_length=255, blank=True)
    
    class Meta:
        verbose_name = "Historique de connexion"
        verbose_name_plural = "Historiques de connexion"
        ordering = ['-date_connexion']
        indexes = [
            models.Index(fields=['utilisateur', '-date_connexion']),
            models.Index(fields=['pharmacie', '-date_connexion']),
        ]
    
    def __str__(self):
        return f"{self.utilisateur.email} - {self.date_connexion}"


class HistoriqueModificationPharmacie(models.Model):
    """
    Historique des modifications des paramètres critiques de la pharmacie
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacie = models.ForeignKey(Pharmacie, on_delete=models.CASCADE, related_name='historique_modifications')
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.SET_NULL, null=True)
    
    champ_modifie = models.CharField(max_length=100)
    ancienne_valeur = models.TextField(blank=True)
    nouvelle_valeur = models.TextField(blank=True)
    date_modification = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Historique de modification"
        verbose_name_plural = "Historiques de modifications"
        ordering = ['-date_modification']
        indexes = [
            models.Index(fields=['pharmacie', '-date_modification']),
        ]
    
    def __str__(self):
        return f"{self.pharmacie.nom_commercial} - {self.champ_modifie} - {self.date_modification}"
