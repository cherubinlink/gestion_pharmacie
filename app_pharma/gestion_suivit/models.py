"""
Modèles pour le Suivi Médical & Relation Client
Application 7 : Suivi médical, historique patient, dossiers médicaux
Partie 1 : Profils médicaux, médecins, pathologies, allergies
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, EmailValidator, FileExtensionValidator
from django.utils import timezone
from decimal import Decimal
import uuid

# Create your models here.

# ============================================================================
# MODÈLES MÉDECINS ET PROFESSIONNELS DE SANTÉ
# ============================================================================

class Doctor(models.Model):
    """Médecin référent"""
    SPECIALITY_CHOICES = [
        ('general_practitioner', 'Médecin généraliste'),
        ('cardiologist', 'Cardiologue'),
        ('dermatologist', 'Dermatologue'),
        ('endocrinologist', 'Endocrinologue'),
        ('gastroenterologist', 'Gastro-entérologue'),
        ('gynecologist', 'Gynécologue'),
        ('neurologist', 'Neurologue'),
        ('ophthalmologist', 'Ophtalmologue'),
        ('orthopedist', 'Orthopédiste'),
        ('otolaryngologist', 'ORL'),
        ('pediatrician', 'Pédiatre'),
        ('pneumologist', 'Pneumologue'),
        ('psychiatrist', 'Psychiatre'),
        ('urologist', 'Urologue'),
        ('other', 'Autre'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacie = models.ForeignKey(
        'gestion_compte.Pharmacie',
        on_delete=models.CASCADE,
        related_name='doctors',
        verbose_name="Pharmacie"
    )
    
    # Identité
    doctor_code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Code médecin"
    )
    first_name = models.CharField(max_length=100, verbose_name="Prénom")
    last_name = models.CharField(max_length=100, verbose_name="Nom")
    title = models.CharField(
        max_length=10,
        choices=[('Dr', 'Dr'), ('Pr', 'Pr')],
        default='Dr',
        verbose_name="Titre"
    )
    
    # Spécialité
    speciality = models.CharField(
        max_length=50,
        choices=SPECIALITY_CHOICES,
        verbose_name="Spécialité"
    )
    
    # Contact
    phone = models.CharField(max_length=20, verbose_name="Téléphone")
    mobile = models.CharField(max_length=20, blank=True, verbose_name="Mobile")
    email = models.EmailField(
        blank=True,
        validators=[EmailValidator()],
        verbose_name="Email"
    )
    
    # Adresse
    address = models.TextField(blank=True, verbose_name="Adresse")
    city = models.CharField(max_length=100, blank=True, verbose_name="Ville")
    
    # Informations professionnelles
    license_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Numéro d'ordre du conseil",
        verbose_name="N° d'ordre"
    )
    hospital = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Hôpital/Clinique"
    )
    
    # Statut
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    
    # Notes
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'medical_doctors'
        ordering = ['last_name', 'first_name']
        verbose_name = "Médecin"
        verbose_name_plural = "Médecins"
        indexes = [
            models.Index(fields=['pharmacie', 'speciality']),
            models.Index(fields=['license_number']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.title} {self.first_name} {self.last_name} - {self.get_speciality_display()}"
    
    def get_full_name(self):
        return f"{self.title} {self.first_name} {self.last_name}"


# ============================================================================
# MODÈLES PROFIL MÉDICAL PATIENT
# ============================================================================

class MedicalProfile(models.Model):
    """Profil médical sécurisé du patient"""
    BLOOD_TYPE_CHOICES = [
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-'),
        ('unknown', 'Non renseigné'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.OneToOneField(
        'gestion_rh.Client',
        on_delete=models.CASCADE,
        related_name='medical_profile',
        verbose_name="Patient"
    )
    
    # Informations médicales de base
    blood_type = models.CharField(
        max_length=10,
        choices=BLOOD_TYPE_CHOICES,
        default='unknown',
        verbose_name="Groupe sanguin"
    )
    height = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Taille en cm",
        verbose_name="Taille (cm)"
    )
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Poids en kg",
        verbose_name="Poids (kg)"
    )
    
    # Médecins référents
    primary_doctor = models.ForeignKey(
        Doctor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='primary_patients',
        verbose_name="Médecin traitant"
    )
    
    # Informations d'urgence
    emergency_contact_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Nom contact d'urgence"
    )
    emergency_contact_phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Téléphone contact d'urgence"
    )
    emergency_contact_relation = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Lien avec contact d'urgence"
    )
    
    # Assurance
    insurance_provider = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Assureur"
    )
    insurance_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Numéro d'assurance"
    )
    
    # Consentement et confidentialité
    consent_data_usage = models.BooleanField(
        default=False,
        help_text="Consentement pour l'utilisation des données médicales",
        verbose_name="Consentement données"
    )
    consent_communication = models.BooleanField(
        default=False,
        help_text="Consentement pour recevoir des communications",
        verbose_name="Consentement communication"
    )
    
    # Notes médicales générales
    medical_notes = models.TextField(
        blank=True,
        verbose_name="Notes médicales"
    )
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_checkup_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Dernière consultation"
    )
    
    class Meta:
        db_table = 'medical_profiles'
        verbose_name = "Profil médical"
        verbose_name_plural = "Profils médicaux"
        indexes = [
            models.Index(fields=['patient']),
        ]
    
    def __str__(self):
        return f"Profil médical - {self.patient.get_full_name()}"
    
    def calculate_bmi(self):
        """Calcule l'IMC (Indice de Masse Corporelle)"""
        if self.height and self.weight:
            height_m = float(self.height) / 100
            return float(self.weight) / (height_m ** 2)
        return None

class DoctorPatientLink(models.Model):
    """Lien entre un patient et ses médecins (Many-to-Many amélioré)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        'gestion_rh.Client',
        on_delete=models.CASCADE,
        related_name='doctor_links',
        verbose_name="Patient"
    )
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name='patient_links',
        verbose_name="Médecin"
    )
    
    # Relation
    is_primary = models.BooleanField(
        default=False,
        verbose_name="Médecin traitant"
    )
    relation_type = models.CharField(
        max_length=50,
        choices=[
            ('regular', 'Suivi régulier'),
            ('consultation', 'Consultation ponctuelle'),
            ('specialist', 'Spécialiste'),
        ],
        default='regular',
        verbose_name="Type de relation"
    )
    
    # Dates
    start_date = models.DateField(
        default=timezone.now,
        verbose_name="Date début suivi"
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date fin suivi"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'medical_doctor_patient_links'
        unique_together = [['patient', 'doctor']]
        ordering = ['-is_primary', '-start_date']
        verbose_name = "Lien médecin-patient"
        verbose_name_plural = "Liens médecins-patients"
    
    def __str__(self):
        return f"{self.patient.get_full_name()} - {self.doctor.get_full_name()}"


# ============================================================================
# MODÈLES PATHOLOGIES ET CONDITIONS MÉDICALES
# ============================================================================

class MedicalCondition(models.Model):
    """Pathologie ou condition médicale"""
    CONDITION_TYPE_CHOICES = [
        ('chronic', 'Maladie chronique'),
        ('acute', 'Maladie aiguë'),
        ('genetic', 'Maladie génétique'),
        ('infectious', 'Maladie infectieuse'),
        ('autoimmune', 'Maladie auto-immune'),
        ('mental', 'Trouble mental'),
        ('other', 'Autre'),
    ]
    
    SEVERITY_CHOICES = [
        ('mild', 'Léger'),
        ('moderate', 'Modéré'),
        ('severe', 'Sévère'),
        ('critical', 'Critique'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Identif

    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Code CIM-10 ou code interne",
        verbose_name="Code"
    )
    name = models.CharField(max_length=255, verbose_name="Nom")
    condition_type = models.CharField(
        max_length=20,
        choices=CONDITION_TYPE_CHOICES,
        verbose_name="Type de pathologie"
    )
    
    # Description
    description = models.TextField(blank=True, verbose_name="Description")
    symptoms = models.TextField(
        blank=True,
        help_text="Symptômes typiques",
        verbose_name="Symptômes"
    )
    
    # Classification
    category = models.CharField(
        max_length=100,
        blank=True,
        help_text="Ex: Cardiovasculaire, Respiratoire, etc.",
        verbose_name="Catégorie"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="Active")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'medical_conditions'
        ordering = ['name']
        verbose_name = "Pathologie"
        verbose_name_plural = "Pathologies"
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['condition_type']),
            models.Index(fields=['category']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class PatientCondition(models.Model):
    """Pathologie déclarée pour un patient"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('in_remission', 'En rémission'),
        ('resolved', 'Résolue'),
        ('chronic', 'Chronique'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        'gestion_rh.Client',
        on_delete=models.CASCADE,
        related_name='conditions',
        verbose_name="Patient"
    )
    condition = models.ForeignKey(
        MedicalCondition,
        on_delete=models.PROTECT,
        related_name='patient_cases',
        verbose_name="Pathologie"
    )
    
    # Dates
    diagnosis_date = models.DateField(
        default=timezone.now,
        verbose_name="Date de diagnostic"
    )
    resolved_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date de résolution"
    )
    
    # Sévérité et statut
    severity = models.CharField(
        max_length=20,
        choices=MedicalCondition.SEVERITY_CHOICES,
        default='moderate',
        verbose_name="Sévérité"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name="Statut"
    )
    
    # Diagnostic
    diagnosed_by = models.ForeignKey(
        Doctor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='diagnoses',
        verbose_name="Diagnostiqué par"
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        help_text="Notes sur l'évolution, traitement, etc.",
        verbose_name="Notes"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'medical_patient_conditions'
        ordering = ['-diagnosis_date']
        verbose_name = "Pathologie patient"
        verbose_name_plural = "Pathologies patients"
        indexes = [
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['condition', 'status']),
        ]
    
    def __str__(self):
        return f"{self.patient.get_full_name()} - {self.condition.name}"


# ============================================================================
# MODÈLES ALLERGIES
# ============================================================================

class Allergen(models.Model):
    """Allergène (substance, médicament, aliment)"""
    ALLERGEN_TYPE_CHOICES = [
        ('medication', 'Médicament'),
        ('food', 'Aliment'),
        ('environment', 'Environnemental'),
        ('animal', 'Animal'),
        ('insect', 'Insecte'),
        ('chemical', 'Chimique'),
        ('other', 'Autre'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="Nom"
    )
    allergen_type = models.CharField(
        max_length=20,
        choices=ALLERGEN_TYPE_CHOICES,
        verbose_name="Type d'allergène"
    )
    
    # Pour médicaments
    active_substance = models.CharField(
        max_length=255,
        blank=True,
        help_text="Substance active si médicament",
        verbose_name="Substance active"
    )
    
    description = models.TextField(blank=True, verbose_name="Description")
    common_reactions = models.TextField(
        blank=True,
        help_text="Réactions courantes",
        verbose_name="Réactions courantes"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'medical_allergens'
        ordering = ['name']
        verbose_name = "Allergène"
        verbose_name_plural = "Allergènes"
        indexes = [
            models.Index(fields=['allergen_type']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_allergen_type_display()})"



class PatientAllergy(models.Model):
    """Allergie déclarée pour un patient"""
    SEVERITY_CHOICES = [
        ('mild', 'Léger'),
        ('moderate', 'Modéré'),
        ('severe', 'Sévère'),
        ('life_threatening', 'Potentiellement mortel'),
    ]
    
    REACTION_TYPE_CHOICES = [
        ('rash', 'Éruption cutanée'),
        ('hives', 'Urticaire'),
        ('itching', 'Démangeaisons'),
        ('swelling', 'Gonflement'),
        ('breathing_difficulty', 'Difficulté respiratoire'),
        ('anaphylaxis', 'Anaphylaxie'),
        ('nausea', 'Nausées'),
        ('vomiting', 'Vomissements'),
        ('diarrhea', 'Diarrhée'),
        ('other', 'Autre'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        'gestion_rh.Client',
        on_delete=models.CASCADE,
        related_name='patient_allergies',
        verbose_name="Patient"
    )
    allergen = models.ForeignKey(
        Allergen,
        on_delete=models.PROTECT,
        related_name='patient_cases',
        verbose_name="Allergène"
    )
    
    # Détails de l'allergie
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default='moderate',
        verbose_name="Sévérité"
    )
    reaction_type = models.CharField(
        max_length=30,
        choices=REACTION_TYPE_CHOICES,
        verbose_name="Type de réaction"
    )
    
    # Description
    symptoms = models.TextField(
        blank=True,
        help_text="Symptômes observés",
        verbose_name="Symptômes"
    )
    
    # Dates
    first_occurrence_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date première occurrence"
    )
    last_occurrence_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date dernière occurrence"
    )
    
    # Diagnostic
    diagnosed_by = models.ForeignKey(
        Doctor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='allergy_diagnoses',
        verbose_name="Diagnostiqué par"
    )
    
    # Statut
    is_active = models.BooleanField(
        default=True,
        help_text="Allergie toujours active",
        verbose_name="Active"
    )
    
    # Notes
    notes = models.TextField(blank=True, verbose_name="Notes")
    emergency_instructions = models.TextField(
        blank=True,
        help_text="Instructions en cas d'urgence",
        verbose_name="Instructions d'urgence"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'medical_patient_allergies'
        unique_together = [['patient', 'allergen']]
        ordering = ['-severity', 'allergen__name']
        verbose_name = "Allergie patient"
        verbose_name_plural = "Allergies patients"
        indexes = [
            models.Index(fields=['patient', 'is_active']),
            models.Index(fields=['severity']),
        ]
    
    def __str__(self):
        return f"{self.patient.get_full_name()} - {self.allergen.name} ({self.get_severity_display()})"



# ============================================================================
# MODÈLES PRESCRIPTIONS ET ORDONNANCES
# ============================================================================

class Prescription(models.Model):
    """Ordonnance médicale"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Terminée'),
        ('cancelled', 'Annulée'),
        ('expired', 'Expirée'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prescription_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Numéro d'ordonnance"
    )
    
    # Patient et médecin
    patient = models.ForeignKey(
        'gestion_rh.Client',
        on_delete=models.PROTECT,
        related_name='prescriptions',
        verbose_name="Patient"
    )
    doctor = models.ForeignKey(
        'Doctor',
        on_delete=models.PROTECT,
        related_name='prescriptions',
        verbose_name="Médecin prescripteur"
    )
    
    # Dates
    prescription_date = models.DateField(
        default=timezone.now,
        verbose_name="Date de prescription"
    )
    expiry_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date d'expiration de l'ordonnance",
        verbose_name="Date d'expiration"
    )
    
    # Diagnostic
    diagnosis = models.TextField(
        blank=True,
        verbose_name="Diagnostic"
    )
    
    # Statut
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name="Statut"
    )
    
    # Renouvellement
    is_renewable = models.BooleanField(
        default=False,
        verbose_name="Renouvelable"
    )
    renewal_count = models.IntegerField(
        default=0,
        help_text="Nombre de renouvellements autorisés",
        verbose_name="Nombre de renouvellements"
    )
    renewals_remaining = models.IntegerField(
        default=0,
        verbose_name="Renouvellements restants"
    )
    
    # Document
    prescription_file = models.FileField(
        upload_to='prescriptions/%Y/%m/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
        verbose_name="Fichier ordonnance"
    )
    
    # Notes
    notes = models.TextField(blank=True, verbose_name="Notes")
    pharmacist_notes = models.TextField(
        blank=True,
        verbose_name="Notes pharmacien"
    )
    
    # Traçabilité
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    dispensed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Délivrée le"
    )
    dispensed_by = models.ForeignKey(
        'gestion_compte.Utilisateur',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prescriptions_dispensed',
        verbose_name="Délivrée par"
    )
    
    class Meta:
        db_table = 'medical_prescriptions'
        ordering = ['-prescription_date']
        verbose_name = "Ordonnance"
        verbose_name_plural = "Ordonnances"
        indexes = [
            models.Index(fields=['patient', '-prescription_date']),
            models.Index(fields=['doctor', '-prescription_date']),
            models.Index(fields=['prescription_number']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Ordonnance {self.prescription_number} - {self.patient.get_full_name()}"
    
    def is_expired(self):
        """Vérifie si l'ordonnance est expirée"""
        if self.expiry_date:
            return timezone.now().date() > self.expiry_date
        return False


class PrescriptionItem(models.Model):
    """Ligne d'ordonnance (médicament prescrit)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Ordonnance"
    )
    product = models.ForeignKey(
        'gestion_vente.Product',
        on_delete=models.PROTECT,
        related_name='prescription_items',
        verbose_name="Médicament"
    )
    
    # Posologie
    quantity = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Nombre d'unités prescrites",
        verbose_name="Quantité"
    )
    dosage = models.CharField(
        max_length=100,
        help_text="Ex: 500mg, 10ml",
        verbose_name="Dosage"
    )
    frequency = models.CharField(
        max_length=100,
        help_text="Ex: 3 fois par jour, matin et soir",
        verbose_name="Fréquence"
    )
    duration = models.CharField(
        max_length=100,
        help_text="Ex: 7 jours, 1 mois",
        verbose_name="Durée"
    )
    
    # Instructions
    instructions = models.TextField(
        blank=True,
        help_text="Instructions spécifiques (avant/après repas, etc.)",
        verbose_name="Instructions"
    )
    
    # Substitution
    substitution_allowed = models.BooleanField(
        default=True,
        verbose_name="Substitution autorisée"
    )
    
    # Délivrance
    quantity_dispensed = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Quantité délivrée"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'medical_prescription_items'
        ordering = ['created_at']
        verbose_name = "Ligne d'ordonnance"
        verbose_name_plural = "Lignes d'ordonnances"
    
    def __str__(self):
        return f"{self.product.name} - {self.dosage} - {self.frequency}"



# ============================================================================
# MODÈLES TRAITEMENTS EN COURS
# ============================================================================

class Treatment(models.Model):
    """Traitement suivi par le patient"""
    STATUS_CHOICES = [
        ('active', 'En cours'),
        ('completed', 'Terminé'),
        ('paused', 'Suspendu'),
        ('discontinued', 'Interrompu'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        'gestion_rh.Client',
        on_delete=models.CASCADE,
        related_name='treatments',
        verbose_name="Patient"
    )
    
    # Traitement
    name = models.CharField(
        max_length=255,
        help_text="Nom du traitement",
        verbose_name="Nom"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description"
    )
    
    # Lien avec pathologie
    condition = models.ForeignKey(
        'PatientCondition',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='treatments',
        verbose_name="Pathologie"
    )
    
    # Prescription source
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='treatments',
        verbose_name="Ordonnance source"
    )
    
    # Dates
    start_date = models.DateField(
        default=timezone.now,
        verbose_name="Date de début"
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date de fin prévue"
    )
    actual_end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date de fin réelle"
    )
    
    # Statut
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name="Statut"
    )
    
    # Suivi
    doctor = models.ForeignKey(
        'Doctor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='treatments_supervised',
        verbose_name="Médecin superviseur"
    )
    
    # Rappels
    reminder_enabled = models.BooleanField(
        default=False,
        verbose_name="Rappels activés"
    )
    reminder_frequency = models.CharField(
        max_length=50,
        blank=True,
        help_text="Ex: daily, twice_daily, weekly",
        verbose_name="Fréquence rappels"
    )
    
    # Notes
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'medical_treatments'
        ordering = ['-start_date']
        verbose_name = "Traitement"
        verbose_name_plural = "Traitements"
        indexes = [
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['status', 'end_date']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.patient.get_full_name()}"


class TreatmentMedication(models.Model):
    """Médicament dans un traitement"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    treatment = models.ForeignKey(
        Treatment,
        on_delete=models.CASCADE,
        related_name='medications',
        verbose_name="Traitement"
    )
    product = models.ForeignKey(
        'gestion_vente.Product',
        on_delete=models.PROTECT,
        related_name='treatment_uses',
        verbose_name="Médicament"
    )
    
    # Posologie
    dosage = models.CharField(max_length=100, verbose_name="Dosage")
    frequency = models.CharField(max_length=100, verbose_name="Fréquence")
    instructions = models.TextField(blank=True, verbose_name="Instructions")
    
    # Dates
    start_date = models.DateField(
        default=timezone.now,
        verbose_name="Date début"
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date fin"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'medical_treatment_medications'
        ordering = ['start_date']
        verbose_name = "Médicament traitement"
        verbose_name_plural = "Médicaments traitements"
    
    def __str__(self):
        return f"{self.product.name} - {self.dosage}"




# ============================================================================
# MODÈLES DOSSIERS MÉDICAUX EXTERNES (DME/EMR)
# ============================================================================

class ExternalMedicalRecord(models.Model):
    """Dossier médical externe (EMR/DME)"""
    RECORD_TYPE_CHOICES = [
        ('consultation', 'Compte-rendu consultation'),
        ('lab_result', 'Résultat d\'analyse'),
        ('imaging', 'Imagerie médicale'),
        ('surgery', 'Compte-rendu opération'),
        ('hospitalization', 'Dossier d\'hospitalisation'),
        ('vaccination', 'Carnet de vaccination'),
        ('other', 'Autre'),
    ]
    
    SOURCE_SYSTEM_CHOICES = [
        ('hospital', 'Hôpital'),
        ('clinic', 'Clinique'),
        ('laboratory', 'Laboratoire'),
        ('imaging_center', 'Centre d\'imagerie'),
        ('specialist', 'Médecin spécialiste'),
        ('other', 'Autre'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        'gestion_rh.Client',
        on_delete=models.CASCADE,
        related_name='external_records',
        verbose_name="Patient"
    )
    
    # Identification du dossier
    external_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="ID dans le système externe",
        verbose_name="ID externe"
    )
    record_type = models.CharField(
        max_length=20,
        choices=RECORD_TYPE_CHOICES,
        verbose_name="Type de dossier"
    )
    
    # Source
    source_system = models.CharField(
        max_length=20,
        choices=SOURCE_SYSTEM_CHOICES,
        verbose_name="Système source"
    )
    source_name = models.CharField(
        max_length=255,
        help_text="Nom de l'établissement source",
        verbose_name="Établissement source"
    )
    
    # Contenu
    title = models.CharField(max_length=255, verbose_name="Titre")
    content = models.TextField(
        blank=True,
        help_text="Contenu du document importé",
        verbose_name="Contenu"
    )
    
    # Médecin
    doctor = models.ForeignKey(
        'Doctor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='external_records',
        verbose_name="Médecin"
    )
    
    # Fichier
    document_file = models.FileField(
        upload_to='external_records/%Y/%m/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'dcm'])],
        verbose_name="Fichier document"
    )
    
    # Dates
    record_date = models.DateField(
        help_text="Date du document médical",
        verbose_name="Date du document"
    )
    import_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date d'import"
    )
    
    # Métadonnées d'interopérabilité
    fhir_resource_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Type de ressource FHIR",
        verbose_name="Type ressource FHIR"
    )
    fhir_resource_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="ID ressource FHIR"
    )
    
    # Validation
    is_verified = models.BooleanField(
        default=False,
        help_text="Vérifié par un professionnel de santé",
        verbose_name="Vérifié"
    )
    verified_by = models.ForeignKey(
        'gestion_compte.Utilisateur',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='records_verified',
        verbose_name="Vérifié par"
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Vérifié le"
    )
    
    # Notes
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'medical_external_records'
        ordering = ['-record_date']
        verbose_name = "Dossier médical externe"
        verbose_name_plural = "Dossiers médicaux externes"
        indexes = [
            models.Index(fields=['patient', '-record_date']),
            models.Index(fields=['record_type']),
            models.Index(fields=['external_id']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.patient.get_full_name()} ({self.record_date})"


# ============================================================================
# MODÈLES RENDEZ-VOUS ET INTERACTIONS
# ============================================================================

class Appointment(models.Model):
    """Rendez-vous pharmacie/médecin"""
    APPOINTMENT_TYPE_CHOICES = [
        ('consultation', 'Consultation pharmaceutique'),
        ('medication_review', 'Revue de médication'),
        ('vaccination', 'Vaccination'),
        ('blood_pressure', 'Prise de tension'),
        ('blood_sugar', 'Glycémie'),
        ('advice', 'Conseil pharmaceutique'),
        ('other', 'Autre'),
    ]
    
    STATUS_CHOICES = [
        ('scheduled', 'Planifié'),
        ('confirmed', 'Confirmé'),
        ('completed', 'Effectué'),
        ('cancelled', 'Annulé'),
        ('no_show', 'Absent'),
        ('rescheduled', 'Reporté'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacie = models.ForeignKey(
        'gestion_compte.Pharmacie',
        on_delete=models.CASCADE,
        related_name='appointments',
        verbose_name="Pharmacie"
    )
    
    # Patient
    patient = models.ForeignKey(
        'gestion_rh.Client',
        on_delete=models.CASCADE,
        related_name='appointments',
        verbose_name="Patient"
    )
    
    # Type et détails
    appointment_type = models.CharField(
        max_length=30,
        choices=APPOINTMENT_TYPE_CHOICES,
        verbose_name="Type de rendez-vous"
    )
    reason = models.TextField(
        blank=True,
        verbose_name="Motif"
    )
    
    # Date et heure
    appointment_datetime = models.DateTimeField(
        verbose_name="Date et heure"
    )
    duration_minutes = models.IntegerField(
        default=30,
        validators=[MinValueValidator(5), MaxValueValidator(180)],
        verbose_name="Durée (minutes)"
    )
    
    # Personnel
    pharmacist = models.ForeignKey(
        'gestion_compte.Utilisateur',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='appointments_assigned',
        verbose_name="Pharmacien"
    )
    
    # Statut
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled',
        verbose_name="Statut"
    )
    
    # Rappels
    reminder_sent = models.BooleanField(
        default=False,
        verbose_name="Rappel envoyé"
    )
    reminder_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Rappel envoyé le"
    )
    
    # Notes
    notes = models.TextField(blank=True, verbose_name="Notes")
    completion_notes = models.TextField(
        blank=True,
        help_text="Notes après le rendez-vous",
        verbose_name="Notes de clôture"
    )
    
    # Traçabilité
    created_by = models.ForeignKey(
        'gestion_compte.Utilisateur',
        on_delete=models.SET_NULL,
        null=True,
        related_name='appointments_created',
        verbose_name="Créé par"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'medical_appointments'
        ordering = ['-appointment_datetime']
        verbose_name = "Rendez-vous"
        verbose_name_plural = "Rendez-vous"
        indexes = [
            models.Index(fields=['pharmacie', 'appointment_datetime']),
            models.Index(fields=['patient', '-appointment_datetime']),
            models.Index(fields=['pharmacist', 'appointment_datetime']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.get_appointment_type_display()} - {self.patient.get_full_name()} ({self.appointment_datetime})"


class PatientMessage(models.Model):
    """Message entre patient et pharmacie"""
    MESSAGE_TYPE_CHOICES = [
        ('question', 'Question'),
        ('complaint', 'Réclamation'),
        ('feedback', 'Avis/Suggestion'),
        ('appointment_request', 'Demande RDV'),
        ('renewal_request', 'Demande renouvellement'),
        ('other', 'Autre'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'Nouveau'),
        ('in_progress', 'En cours'),
        ('answered', 'Répondu'),
        ('closed', 'Clôturé'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Basse'),
        ('normal', 'Normale'),
        ('high', 'Haute'),
        ('urgent', 'Urgente'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacie = models.ForeignKey(
        'gestion_compte.Pharmacie',
        on_delete=models.CASCADE,
        related_name='patient_messages',
        verbose_name="Pharmacie"
    )
    patient = models.ForeignKey(
        'gestion_rh.Client',
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name="Patient"
    )
    
    # Type et contenu
    message_type = models.CharField(
        max_length=30,
        choices=MESSAGE_TYPE_CHOICES,
        verbose_name="Type de message"
    )
    subject = models.CharField(max_length=255, verbose_name="Sujet")
    message = models.TextField(verbose_name="Message")
    
    # Priorité et statut
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='normal',
        verbose_name="Priorité"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new',
        verbose_name="Statut"
    )
    
    # Traitement
    assigned_to = models.ForeignKey(
        'gestion_compte.Utilisateur',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='patient_messages_assigned',
        verbose_name="Assigné à"
    )
    response = models.TextField(
        blank=True,
        verbose_name="Réponse"
    )
    responded_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Répondu le"
    )
    responded_by = models.ForeignKey(
        'gestion_compte.Utilisateur',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='patient_messages_responded',
        verbose_name="Répondu par"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'medical_patient_messages'
        ordering = ['-created_at']
        verbose_name = "Message patient"
        verbose_name_plural = "Messages patients"
        indexes = [
            models.Index(fields=['pharmacie', 'status', '-created_at']),
            models.Index(fields=['patient', '-created_at']),
            models.Index(fields=['assigned_to', 'status']),
        ]
    
    def __str__(self):
        return f"{self.subject} - {self.patient.get_full_name()}"



# ============================================================================
# MODÈLES PROGRAMME DE FIDÉLITÉ
# ============================================================================

class LoyaltyProgram(models.Model):
    """Programme de fidélité"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacie = models.OneToOneField(
        'gestion_compte.Pharmacie',
        on_delete=models.CASCADE,
        related_name='loyalty_program',
        verbose_name="Pharmacie"
    )
    
    name = models.CharField(max_length=255, verbose_name="Nom du programme")
    description = models.TextField(blank=True, verbose_name="Description")
    
    # Paramètres points
    points_per_xaf = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('1.00'),
        help_text="Points gagnés pour chaque XAF dépensé",
        verbose_name="Points par XAF"
    )
    points_expiry_months = models.IntegerField(
        default=12,
        help_text="Durée de validité des points en mois",
        verbose_name="Validité points (mois)"
    )
    
    # Paramètres récompenses
    min_points_redemption = models.IntegerField(
        default=100,
        help_text="Nombre minimum de points pour utiliser",
        verbose_name="Points min. utilisation"
    )
    xaf_per_point = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('1.00'),
        help_text="Valeur en XAF de chaque point",
        verbose_name="XAF par point"
    )
    
    # Bonus
    birthday_bonus_points = models.IntegerField(
        default=0,
        verbose_name="Bonus anniversaire"
    )
    referral_bonus_points = models.IntegerField(
        default=0,
        verbose_name="Bonus parrainage"
    )
    
    # Niveaux
    enable_tiers = models.BooleanField(
        default=False,
        help_text="Activer les niveaux de fidélité",
        verbose_name="Activer niveaux"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'crm_loyalty_programs'
        verbose_name = "Programme de fidélité"
        verbose_name_plural = "Programmes de fidélité"
    
    def __str__(self):
        return f"{self.name} - {self.pharmacie.name}"


class LoyaltyTier(models.Model):
    """Niveau de fidélité"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    program = models.ForeignKey(
        LoyaltyProgram,
        on_delete=models.CASCADE,
        related_name='tiers',
        verbose_name="Programme"
    )
    
    name = models.CharField(max_length=100, verbose_name="Nom du niveau")
    description = models.TextField(blank=True, verbose_name="Description")
    
    # Seuils
    min_points = models.IntegerField(
        default=0,
        help_text="Points minimum requis",
        verbose_name="Points minimum"
    )
    min_purchases = models.IntegerField(
        default=0,
        help_text="Nombre d'achats minimum",
        verbose_name="Achats minimum"
    )
    min_amount_spent = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Montant dépensé minimum",
        verbose_name="Montant minimum"
    )
    
    # Avantages
    points_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00'),
        help_text="Multiplicateur de points",
        verbose_name="Multiplicateur points"
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Remise %"
    )
    
    # Ordre
    level = models.IntegerField(
        default=1,
        help_text="Ordre du niveau (1=Bronze, 2=Silver, 3=Gold)",
        verbose_name="Niveau"
    )
    
    # Couleur pour affichage
    color = models.CharField(
        max_length=7,
        default='#6c757d',
        help_text="Couleur hexadécimale",
        verbose_name="Couleur"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'crm_loyalty_tiers'
        ordering = ['level']
        unique_together = [['program', 'level']]
        verbose_name = "Niveau de fidélité"
        verbose_name_plural = "Niveaux de fidélité"
    
    def __str__(self):
        return f"{self.name} (Niveau {self.level})"


class CustomerLoyalty(models.Model):
    """Compte fidélité client"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.OneToOneField(
        'gestion_rh.Client',
        on_delete=models.CASCADE,
        related_name='loyalty_account',
        verbose_name="Client"
    )
    program = models.ForeignKey(
        LoyaltyProgram,
        on_delete=models.PROTECT,
        related_name='customer_accounts',
        verbose_name="Programme"
    )
    
    # Points
    total_points_earned = models.IntegerField(
        default=0,
        verbose_name="Total points gagnés"
    )
    points_balance = models.IntegerField(
        default=0,
        verbose_name="Solde points"
    )
    points_used = models.IntegerField(
        default=0,
        verbose_name="Points utilisés"
    )
    points_expired = models.IntegerField(
        default=0,
        verbose_name="Points expirés"
    )
    
    # Niveau
    current_tier = models.ForeignKey(
        LoyaltyTier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customers',
        verbose_name="Niveau actuel"
    )
    
    # Statistiques
    total_purchases = models.IntegerField(
        default=0,
        verbose_name="Total achats"
    )
    total_amount_spent = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Total dépensé"
    )
    
    # Dates
    enrolled_date = models.DateField(
        default=timezone.now,
        verbose_name="Date d'inscription"
    )
    last_activity_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Dernière activité"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'crm_customer_loyalty'
        verbose_name = "Compte fidélité client"
        verbose_name_plural = "Comptes fidélité clients"
        indexes = [
            models.Index(fields=['customer']),
            models.Index(fields=['program', 'current_tier']),
        ]
    
    def __str__(self):
        return f"{self.customer.get_full_name()} - {self.points_balance} pts"



class LoyaltyTransaction(models.Model):
    """Transaction de points de fidélité"""
    TRANSACTION_TYPE_CHOICES = [
        ('earn', 'Gain de points'),
        ('redeem', 'Utilisation de points'),
        ('expire', 'Expiration de points'),
        ('bonus', 'Bonus'),
        ('adjustment', 'Ajustement'),
        ('refund', 'Remboursement'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer_loyalty = models.ForeignKey(
        CustomerLoyalty,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name="Compte fidélité"
    )
    
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES,
        verbose_name="Type de transaction"
    )
    points = models.IntegerField(
        help_text="Positif pour gains, négatif pour utilisation",
        verbose_name="Points"
    )
    
    # Référence
    sale = models.ForeignKey(
        'gestion_vente.Sale',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='loyalty_transactions',
        verbose_name="Vente"
    )
    
    # Description
    description = models.CharField(max_length=255, verbose_name="Description")
    
    # Expiration
    expires_at = models.DateField(
        null=True,
        blank=True,
        verbose_name="Expire le"
    )
    
    transaction_date = models.DateTimeField(
        default=timezone.now,
        verbose_name="Date transaction"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'crm_loyalty_transactions'
        ordering = ['-transaction_date']
        verbose_name = "Transaction fidélité"
        verbose_name_plural = "Transactions fidélité"
        indexes = [
            models.Index(fields=['customer_loyalty', '-transaction_date']),
        ]
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.points} pts"



# ============================================================================
# MODÈLES CAMPAGNES MARKETING
# ============================================================================

class MarketingCampaign(models.Model):
    """Campagne marketing"""
    CAMPAIGN_TYPE_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Notification push'),
        ('social', 'Réseaux sociaux'),
        ('mixed', 'Mixte'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('scheduled', 'Planifiée'),
        ('running', 'En cours'),
        ('completed', 'Terminée'),
        ('paused', 'En pause'),
        ('cancelled', 'Annulée'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacie = models.ForeignKey(
        'gestion_compte.Pharmacie',
        on_delete=models.CASCADE,
        related_name='marketing_campaigns',
        verbose_name="Pharmacie"
    )
    
    # Identification
    name = models.CharField(max_length=255, verbose_name="Nom de la campagne")
    description = models.TextField(blank=True, verbose_name="Description")
    campaign_type = models.CharField(
        max_length=20,
        choices=CAMPAIGN_TYPE_CHOICES,
        verbose_name="Type de campagne"
    )
    
    # Contenu
    subject = models.CharField(
        max_length=255,
        blank=True,
        help_text="Sujet email ou titre SMS",
        verbose_name="Sujet"
    )
    message_body = models.TextField(
        help_text="Corps du message",
        verbose_name="Message"
    )
    
    # Cible
    target_segment = models.CharField(
        max_length=100,
        blank=True,
        help_text="Segment ciblé",
        verbose_name="Segment cible"
    )
    
    # Planification
    scheduled_datetime = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date d'envoi prévue"
    )
    start_datetime = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de début"
    )
    end_datetime = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de fin"
    )
    
    # Statut
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name="Statut"
    )
    
    # Statistiques
    total_recipients = models.IntegerField(
        default=0,
        verbose_name="Destinataires"
    )
    total_sent = models.IntegerField(
        default=0,
        verbose_name="Envoyés"
    )
    total_delivered = models.IntegerField(
        default=0,
        verbose_name="Délivrés"
    )
    total_opened = models.IntegerField(
        default=0,
        verbose_name="Ouverts"
    )
    total_clicked = models.IntegerField(
        default=0,
        verbose_name="Cliqués"
    )
    total_conversions = models.IntegerField(
        default=0,
        verbose_name="Conversions"
    )
    
    # ROI
    campaign_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Coût campagne"
    )
    revenue_generated = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Revenus générés"
    )
    
    # Traçabilité
    created_by = models.ForeignKey(
        'gestion_compte.Utilisateur',
        on_delete=models.SET_NULL,
        null=True,
        related_name='campaigns_created',
        verbose_name="Créé par"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'crm_marketing_campaigns'
        ordering = ['-created_at']
        verbose_name = "Campagne marketing"
        verbose_name_plural = "Campagnes marketing"
        indexes = [
            models.Index(fields=['pharmacie', 'status']),
            models.Index(fields=['scheduled_datetime']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_campaign_type_display()})"
    
    def calculate_roi(self):
        """Calcule le ROI de la campagne"""
        if self.campaign_cost > 0:
            return ((self.revenue_generated - self.campaign_cost) / self.campaign_cost) * 100
        return Decimal('0.00')



class CampaignRecipient(models.Model):
    """Destinataire d'une campagne"""
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('sent', 'Envoyé'),
        ('delivered', 'Délivré'),
        ('opened', 'Ouvert'),
        ('clicked', 'Cliqué'),
        ('converted', 'Converti'),
        ('bounced', 'Rejeté'),
        ('unsubscribed', 'Désinscrit'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        MarketingCampaign,
        on_delete=models.CASCADE,
        related_name='recipients',
        verbose_name="Campagne"
    )
    customer = models.ForeignKey(
        'gestion_rh.Client',
        on_delete=models.CASCADE,
        related_name='campaign_receipts',
        verbose_name="Client"
    )
    
    # Statut
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Statut"
    )
    
    # Dates
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Envoyé le"
    )
    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Délivré le"
    )
    opened_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Ouvert le"
    )
    clicked_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Cliqué le"
    )
    
    # Conversion
    converted = models.BooleanField(
        default=False,
        verbose_name="Converti"
    )
    conversion_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Montant conversion"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'crm_campaign_recipients'
        unique_together = [['campaign', 'customer']]
        ordering = ['created_at']
        verbose_name = "Destinataire campagne"
        verbose_name_plural = "Destinataires campagnes"
        indexes = [
            models.Index(fields=['campaign', 'status']),
        ]
    
    def __str__(self):
        return f"{self.customer.get_full_name()} - {self.campaign.name}"


# ============================================================================
# MODÈLES SEGMENTATION CLIENTS
# ============================================================================

class CustomerSegment(models.Model):
    """Segment de clientèle"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacie = models.ForeignKey(
        'gestion_compte.Pharmacie',
        on_delete=models.CASCADE,
        related_name='customer_segments',
        verbose_name="Pharmacie"
    )
    
    name = models.CharField(max_length=255, verbose_name="Nom du segment")
    description = models.TextField(blank=True, verbose_name="Description")
    
    # Critères de segmentation
    age_min = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(150)],
        verbose_name="Âge minimum"
    )
    age_max = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(150)],
        verbose_name="Âge maximum"
    )
    gender = models.CharField(
        max_length=10,
        blank=True,
        choices=[('M', 'Homme'), ('F', 'Femme')],
        verbose_name="Sexe"
    )
    
    # Comportement d'achat
    min_purchases = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        verbose_name="Achats minimum"
    )
    min_amount_spent = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Montant dépensé minimum"
    )
    days_since_last_purchase = models.IntegerField(
        null=True,
        blank=True,
        help_text="Jours depuis dernier achat",
        verbose_name="Jours depuis dernier achat"
    )
    
    # Géographie
    city = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Ville"
    )
    
    # Fidélité
    loyalty_tier = models.ForeignKey(
        LoyaltyTier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='segments',
        verbose_name="Niveau fidélité"
    )
    
    # Calcul automatique
    is_dynamic = models.BooleanField(
        default=True,
        help_text="Recalculer automatiquement les membres",
        verbose_name="Dynamique"
    )
    
    # Statistiques
    customer_count = models.IntegerField(
        default=0,
        verbose_name="Nombre de clients"
    )
    last_calculated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Dernière MAJ"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'crm_customer_segments'
        ordering = ['name']
        verbose_name = "Segment client"
        verbose_name_plural = "Segments clients"
        indexes = [
            models.Index(fields=['pharmacie', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.customer_count} clients)"


# ============================================================================
# MODÈLES LEADS ET PROSPECTS
# ============================================================================

class Lead(models.Model):
    """Lead / Prospect"""
    SOURCE_CHOICES = [
        ('website', 'Site web'),
        ('social_media', 'Réseaux sociaux'),
        ('referral', 'Recommandation'),
        ('walk_in', 'Visite en pharmacie'),
        ('phone', 'Téléphone'),
        ('email', 'Email'),
        ('event', 'Événement'),
        ('other', 'Autre'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'Nouveau'),
        ('contacted', 'Contacté'),
        ('qualified', 'Qualifié'),
        ('converted', 'Converti'),
        ('lost', 'Perdu'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacie = models.ForeignKey(
        'gestion_compte.Pharmacie',
        on_delete=models.CASCADE,
        related_name='leads',
        verbose_name="Pharmacie"
    )
    
    # Identité
    first_name = models.CharField(max_length=100, verbose_name="Prénom")
    last_name = models.CharField(max_length=100, verbose_name="Nom")
    email = models.EmailField(blank=True, verbose_name="Email")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone")
    
    # Source
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        verbose_name="Source"
    )
    source_details = models.TextField(
        blank=True,
        verbose_name="Détails source"
    )
    
    # Intérêt
    interest_area = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Domaine d'intérêt"
    )
    
    # Statut
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new',
        verbose_name="Statut"
    )
    
    # Assignment
    assigned_to = models.ForeignKey(
        'gestion_compte.Utilisateur',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leads_assigned',
        verbose_name="Assigné à"
    )
    
    # Conversion
    converted_to_customer = models.ForeignKey(
        'gestion_rh.Client',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lead_source',
        verbose_name="Converti en client"
    )
    converted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Converti le"
    )
    
    # Notes
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'crm_leads'
        ordering = ['-created_at']
        verbose_name = "Lead"
        verbose_name_plural = "Leads"
        indexes = [
            models.Index(fields=['pharmacie', 'status']),
            models.Index(fields=['assigned_to', 'status']),
        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_status_display()})"


# ============================================================================
# MODÈLES RAPPELS AUTOMATIQUES
# ============================================================================

class AutomatedReminder(models.Model):
    """Rappel automatique"""
    REMINDER_TYPE_CHOICES = [
        ('medication_renewal', 'Renouvellement traitement'),
        ('appointment', 'Rendez-vous'),
        ('medication_time', 'Prise de médicament'),
        ('birthday', 'Anniversaire'),
        ('inactive_customer', 'Client inactif'),
        ('loyalty_points', 'Points fidélité'),
        ('other', 'Autre'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('sent', 'Envoyé'),
        ('failed', 'Échoué'),
        ('cancelled', 'Annulé'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacie = models.ForeignKey(
        'gestion_compte.Pharmacie',
        on_delete=models.CASCADE,
        related_name='automated_reminders',
        verbose_name="Pharmacie"
    )
    customer = models.ForeignKey(
        'gestion_rh.Client',
        on_delete=models.CASCADE,
        related_name='reminders',
        verbose_name="Client"
    )
    
    # Type et contenu
    reminder_type = models.CharField(
        max_length=30,
        choices=REMINDER_TYPE_CHOICES,
        verbose_name="Type de rappel"
    )
    message = models.TextField(verbose_name="Message")
    
    # Envoi
    send_via_sms = models.BooleanField(default=False, verbose_name="Envoyer par SMS")
    send_via_email = models.BooleanField(default=False, verbose_name="Envoyer par Email")
    send_via_push = models.BooleanField(default=False, verbose_name="Envoyer par Push")
    
    # Planification
    scheduled_datetime = models.DateTimeField(verbose_name="Date d'envoi prévue")
    
    # Statut
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Statut"
    )
    
    # Envoi effectif
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Envoyé le"
    )
    
    # Références
    treatment = models.ForeignKey(
        'Treatment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reminders',
        verbose_name="Traitement"
    )
    appointment = models.ForeignKey(
        'Appointment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reminders',
        verbose_name="Rendez-vous"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'crm_automated_reminders'
        ordering = ['scheduled_datetime']
        verbose_name = "Rappel automatique"
        verbose_name_plural = "Rappels automatiques"
        indexes = [
            models.Index(fields=['pharmacie', 'status', 'scheduled_datetime']),
            models.Index(fields=['customer', 'scheduled_datetime']),
        ]
    
    def __str__(self):
        return f"{self.get_reminder_type_display()} - {self.customer.get_full_name()}"




