from django.db import models
from gestion_compte.models import Utilisateur, Pharmacie
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid

# Create your models here.

"""
Modèles pour le suivi, la performance et l'historique des employés
"""


class TimeEntry(models.Model):
    """Enregistrement des pointages (entrées/sorties)"""
    ENTRY_TYPE_CHOICES = [
        ('clock_in', 'Entrée'),
        ('clock_out', 'Sortie'),
        ('break_start', 'Début de pause'),
        ('break_end', 'Fin de pause'),
    ]
    
    METHOD_CHOICES = [
        ('badge', 'Badge'),
        ('qr_code', 'QR Code'),
        ('biometric', 'Biométrie'),
        ('pin', 'Code PIN'),
        ('manual', 'Manuel'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        'Employee',
        on_delete=models.CASCADE,
        related_name='time_entries'
    )
    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPE_CHOICES)
    timestamp = models.DateTimeField()
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    location = models.JSONField(
        null=True,
        blank=True,
        help_text="Coordonnées GPS si applicable"
    )
    device_info = models.JSONField(
        null=True,
        blank=True,
        help_text="Informations sur le dispositif utilisé"
    )
    is_manual = models.BooleanField(default=False)
    manual_entry_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='manual_time_entries'
    )
    manual_entry_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'time_entries'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['employee', '-timestamp']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['entry_type', 'employee']),
        ]
    
    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.get_entry_type_display()} ({self.timestamp})"
    
    
class WorkSession(models.Model):
    """Session de travail calculée à partir des pointages"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        'Employee',
        on_delete=models.CASCADE,
        related_name='work_sessions'
    )
    date = models.DateField()
    clock_in = models.ForeignKey(
        TimeEntry,
        on_delete=models.CASCADE,
        related_name='sessions_started'
    )
    clock_out = models.ForeignKey(
        TimeEntry,
        on_delete=models.CASCADE,
        related_name='sessions_ended',
        null=True,
        blank=True
    )
    scheduled_start = models.TimeField()
    scheduled_end = models.TimeField()
    actual_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    break_duration = models.IntegerField(
        default=0,
        help_text="Durée totale des pauses en minutes"
    )
    overtime_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    is_late = models.BooleanField(default=False)
    late_duration = models.IntegerField(
        default=0,
        help_text="Durée du retard en minutes"
    )
    is_complete = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'work_sessions'
        ordering = ['-date']
        indexes = [
            models.Index(fields=['employee', '-date']),
            models.Index(fields=['date']),
            models.Index(fields=['is_late']),
        ]
    
    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.date} ({self.actual_hours}h)"


class Commission(models.Model):
    """Commissions des employés"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        'Employee',
        on_delete=models.CASCADE,
        related_name='commissions'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    commission_type = models.CharField(max_length=100)
    description = models.TextField()
    calculation_basis = models.JSONField(
        help_text="Base de calcul (ventes, objectifs, etc.)"
    )
    period_start = models.DateField()
    period_end = models.DateField()
    is_paid = models.BooleanField(default=False)
    paid_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        related_name='commissions_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'commissions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['employee', '-created_at']),
            models.Index(fields=['is_paid', 'period_end']),
        ]
    
    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.amount} ({self.commission_type})"



class Promotion(models.Model):
    """Promotions et évolutions de carrière"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        'Employee',
        on_delete=models.CASCADE,
        related_name='promotions'
    )
    old_role = models.ForeignKey(
        'Role',
        on_delete=models.PROTECT,
        related_name='promotions_from'
    )
    new_role = models.ForeignKey(
        'Role',
        on_delete=models.PROTECT,
        related_name='promotions_to'
    )
    old_salary = models.DecimalField(max_digits=10, decimal_places=2)
    new_salary = models.DecimalField(max_digits=10, decimal_places=2)
    promotion_date = models.DateField()
    reason = models.TextField()
    approved_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        related_name='promotions_approved'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'promotions'
        ordering = ['-promotion_date']
        indexes = [
            models.Index(fields=['employee', '-promotion_date']),
        ]
    
    def __str__(self):
        return f"{self.employee.user.get_full_name()}: {self.old_role.name} → {self.new_role.name}"
    

class Warning(models.Model):
    """Avertissements disciplinaires"""
    SEVERITY_CHOICES = [
        ('verbal', 'Avertissement verbal'),
        ('written', 'Avertissement écrit'),
        ('final', 'Avertissement final'),
        ('suspension', 'Suspension'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        'Employee',
        on_delete=models.CASCADE,
        related_name='warnings'
    )
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    date_issued = models.DateField()
    reason = models.TextField()
    description = models.TextField()
    action_taken = models.TextField()
    issued_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        related_name='warnings_issued'
    )
    documents = models.JSONField(default=list)
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    employee_response = models.TextField(blank=True)
    expiry_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date d'expiration de l'avertissement"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'warnings'
        ordering = ['-date_issued']
        indexes = [
            models.Index(fields=['employee', '-date_issued']),
            models.Index(fields=['severity']),
        ]
    
    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.get_severity_display()} ({self.date_issued})"



class Training(models.Model):
    """Formations suivies par les employés"""
    STATUS_CHOICES = [
        ('scheduled', 'Planifié'),
        ('in_progress', 'En cours'),
        ('completed', 'Terminé'),
        ('cancelled', 'Annulé'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        'Employee',
        on_delete=models.CASCADE,
        related_name='trainings'
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    provider = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    duration_hours = models.DecimalField(max_digits=5, decimal_places=2)
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled'
    )
    certificate_obtained = models.BooleanField(default=False)
    certificate_url = models.URLField(blank=True)
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    feedback = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'trainings'
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['employee', 'status']),
            models.Index(fields=['start_date', 'end_date']),
        ]
    
    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.title}"


class PerformanceReview(models.Model):
    """Évaluations de performance"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        'Employee',
        on_delete=models.CASCADE,
        related_name='performance_reviews'
    )
    review_period_start = models.DateField()
    review_period_end = models.DateField()
    review_date = models.DateField()
    reviewer = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reviews_conducted'
    )
    overall_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    criteria_scores = models.JSONField(
        help_text="Scores par critère: {critère: score}"
    )
    strengths = models.TextField()
    areas_for_improvement = models.TextField()
    goals = models.JSONField(
        default=list,
        help_text="Objectifs fixés pour la prochaine période"
    )
    employee_comments = models.TextField(blank=True)
    action_plan = models.TextField()
    next_review_date = models.DateField()
    documents = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'performance_reviews'
        ordering = ['-review_date']
        indexes = [
            models.Index(fields=['employee', '-review_date']),
        ]
    
    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.review_date} (Rating: {self.overall_rating})"


class PerformanceMetrics(models.Model):
    """Métriques de performance calculées automatiquement"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        'Employee',
        on_delete=models.CASCADE,
        related_name='performance_metrics'
    )
    period_start = models.DateField()
    period_end = models.DateField()
    total_sales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_transactions = models.IntegerField(default=0)
    average_transaction_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    punctuality_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('100.00'),
        help_text="Pourcentage de ponctualité"
    )
    attendance_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('100.00'),
        help_text="Pourcentage de présence"
    )
    customer_satisfaction_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    efficiency_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    custom_metrics = models.JSONField(
        default=dict,
        help_text="Métriques personnalisées additionnelles"
    )
    calculated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'performance_metrics'
        unique_together = [['employee', 'period_start', 'period_end']]
        ordering = ['-period_end']
        indexes = [
            models.Index(fields=['employee', '-period_end']),
        ]
    
    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.period_start} to {self.period_end}"


class Bonus(models.Model):
    """Primes et bonus des employés"""
    BONUS_TYPE_CHOICES = [
        ('performance', 'Prime de performance'),
        ('holiday', 'Prime de vacances'),
        ('annual', 'Prime annuelle'),
        ('exceptional', 'Prime exceptionnelle'),
        ('goal', 'Prime sur objectif'),
        ('other', 'Autre'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        'Employee',
        on_delete=models.CASCADE,
        related_name='bonuses'
    )
    bonus_type = models.CharField(max_length=20, choices=BONUS_TYPE_CHOICES)
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    description = models.TextField()
    calculation_basis = models.JSONField(
        null=True,
        blank=True,
        help_text="Base de calcul si applicable"
    )
    period_start = models.DateField()
    period_end = models.DateField()
    is_paid = models.BooleanField(default=False)
    paid_date = models.DateField(null=True, blank=True)
    approved_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        related_name='bonuses_approved'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'bonuses'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['employee', '-created_at']),
            models.Index(fields=['is_paid']),
        ]
    
    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.get_bonus_type_display()} ({self.amount})"



# ============================================================================
# MODÈLES DE BASE - RÔLES ET EMPLOYÉS
# ============================================================================

class Role(models.Model):
    """Modèle pour les rôles personnalisables"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name="Nom du rôle")
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='roles',
        null=True,
        blank=True,
        help_text="Si null, c'est un rôle global"
    )
    description = models.TextField(blank=True, verbose_name="Description")
    permissions = models.JSONField(
        default=dict,
        help_text="Structure: {module: [permissions]}"
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Rôles par défaut du système (pharmacien, assistant, etc.)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'hr_roles'
        unique_together = [['name', 'pharmacie']]
        ordering = ['name']
        verbose_name = "Rôle"
        verbose_name_plural = "Rôles"
        indexes = [
            models.Index(fields=['pharmacie', 'is_default']),
        ]
    
    def __str__(self):
        if self.pharmacie:
            return f"{self.name} ({self.pharmacie.nom})"
        return f"{self.name} (Global)"


class Employee(models.Model):
    """Modèle pour les employés des pharmacies"""
    EMPLOYMENT_STATUS = [
        ('active', 'Actif'),
        ('on_leave', 'En congé'),
        ('suspended', 'Suspendu'),
        ('terminated', 'Licencié'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.OneToOneField(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='employee_profile',
        verbose_name="Utilisateur"
    )
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='employees',
        verbose_name="Pharmacie"
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name='employees',
        verbose_name="Rôle"
    )
    employee_id = models.CharField(
        max_length=50, 
        unique=True,
        verbose_name="ID Employé"
    )
    salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Salaire"
    )
    hire_date = models.DateField(verbose_name="Date d'embauche")
    employment_status = models.CharField(
        max_length=20,
        choices=EMPLOYMENT_STATUS,
        default='active',
        verbose_name="Statut d'emploi"
    )
    emergency_contact_name = models.CharField(
        max_length=255, 
        blank=True,
        verbose_name="Contact d'urgence (nom)"
    )
    emergency_contact_phone = models.CharField(
        max_length=20, 
        blank=True,
        verbose_name="Contact d'urgence (téléphone)"
    )
    documents = models.JSONField(
        default=list,
        help_text="Liste des documents (CV, diplômes, etc.)"
    )
    notes = models.TextField(blank=True, verbose_name="Notes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'hr_employees'
        ordering = ['-hire_date']
        verbose_name = "Employé"
        verbose_name_plural = "Employés"
        indexes = [
            models.Index(fields=['pharmacie', 'employment_status']),
            models.Index(fields=['employee_id']),
            models.Index(fields=['role']),
        ]
    
    def __str__(self):
        return f"{self.utilisateur.get_full_name()} - {self.employee_id}"
    
    def get_full_name(self):
        """Retourne le nom complet de l'employé"""
        return self.utilisateur.get_full_name()


class EmployeeTransferHistory(models.Model):
    """Historique des transferts d'employés entre pharmacies"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='transfer_history',
        verbose_name="Employé"
    )
    from_pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='transfers_out',
        verbose_name="De la pharmacie"
    )
    to_pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='transfers_in',
        verbose_name="Vers la pharmacie"
    )
    transfer_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de transfert"
    )
    reason = models.TextField(verbose_name="Raison du transfert")
    transferred_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        related_name='employee_transfers_made',
        verbose_name="Transféré par"
    )
    old_salary = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Ancien salaire"
    )
    new_salary = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Nouveau salaire"
    )
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        db_table = 'hr_employee_transfer_history'
        ordering = ['-transfer_date']
        verbose_name = "Historique de transfert d'employé"
        verbose_name_plural = "Historiques de transferts d'employés"
        indexes = [
            models.Index(fields=['employee', '-transfer_date']),
            models.Index(fields=['from_pharmacie']),
            models.Index(fields=['to_pharmacie']),
        ]
    
    def __str__(self):
        return f"{self.employee.get_full_name()}: {self.from_pharmacie.nom} → {self.to_pharmacie.nom}"



# ============================================================================
# MODÈLE CLIENT
# ============================================================================

class Client(models.Model):
    """Modèle pour les clients"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.OneToOneField(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='client_profile',
        verbose_name="Utilisateur"
    )
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='clients',
        verbose_name="Pharmacie"
    )
    client_number = models.CharField(
        max_length=50, 
        unique=True,
        verbose_name="Numéro client"
    )
    loyalty_points = models.IntegerField(
        default=0,
        verbose_name="Points de fidélité"
    )
    medical_notes = models.TextField(
        blank=True, 
        help_text="Notes médicales confidentielles",
        verbose_name="Notes médicales"
    )
    allergies = models.JSONField(
        default=list, 
        help_text="Liste des allergies",
        verbose_name="Allergies"
    )
    preferred_payment_method = models.CharField(
        max_length=50, 
        blank=True,
        verbose_name="Méthode de paiement préférée"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Actif"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'hr_clients'
        ordering = ['-created_at']
        verbose_name = "Client"
        verbose_name_plural = "Clients"
        indexes = [
            models.Index(fields=['pharmacie', 'is_active']),
            models.Index(fields=['client_number']),
        ]
    
    def __str__(self):
        return f"{self.utilisateur.get_full_name()} - {self.client_number}"


class ClientTransferHistory(models.Model):
    """Historique des transferts de clients entre pharmacies"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='transfer_history',
        verbose_name="Client"
    )
    from_pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='client_transfers_out',
        verbose_name="De la pharmacie"
    )
    to_pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='client_transfers_in',
        verbose_name="Vers la pharmacie"
    )
    transfer_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de transfert"
    )
    reason = models.TextField(verbose_name="Raison du transfert")
    transferred_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        related_name='client_transfers_made',
        verbose_name="Transféré par"
    )
    loyalty_points_transferred = models.IntegerField(
        default=0,
        verbose_name="Points de fidélité transférés"
    )
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        db_table = 'hr_client_transfer_history'
        ordering = ['-transfer_date']
        verbose_name = "Historique de transfert de client"
        verbose_name_plural = "Historiques de transferts de clients"
        indexes = [
            models.Index(fields=['client', '-transfer_date']),
        ]
    
    def __str__(self):
        return f"{self.client.utilisateur.get_full_name()}: {self.from_pharmacie.nom} → {self.to_pharmacie.nom}"



# ============================================================================
# MODÈLES DE PLANNING
# ============================================================================

class WorkSchedule(models.Model):
    """Planning de travail des employés"""
    SHIFT_CHOICES = [
        ('day', 'Jour'),
        ('night', 'Nuit'),
        ('custom', 'Personnalisé'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='work_schedules',
        verbose_name="Employé"
    )
    date = models.DateField(verbose_name="Date")
    shift_type = models.CharField(
        max_length=20, 
        choices=SHIFT_CHOICES,
        verbose_name="Type de shift"
    )
    start_time = models.TimeField(verbose_name="Heure de début")
    end_time = models.TimeField(verbose_name="Heure de fin")
    is_recurring = models.BooleanField(
        default=False,
        verbose_name="Récurrent"
    )
    recurrence_rule = models.JSONField(
        null=True,
        blank=True,
        help_text="Règle de récurrence (RRULE)",
        verbose_name="Règle de récurrence"
    )
    notes = models.TextField(blank=True, verbose_name="Notes")
    created_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        related_name='schedules_created',
        verbose_name="Créé par"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'hr_work_schedules'
        ordering = ['date', 'start_time']
        unique_together = [['employee', 'date', 'start_time']]
        verbose_name = "Planning de travail"
        verbose_name_plural = "Plannings de travail"
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['date', 'shift_type']),
        ]
    
    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.date} ({self.get_shift_type_display()})"



# ============================================================================
# MODÈLES DE CONGÉS ET ABSENCES
# ============================================================================

class LeaveRequest(models.Model):
    """Demandes de congés"""
    LEAVE_TYPE_CHOICES = [
        ('annual', 'Congé annuel'),
        ('sick', 'Congé maladie'),
        ('maternity', 'Congé maternité'),
        ('paternity', 'Congé paternité'),
        ('unpaid', 'Congé sans solde'),
        ('emergency', "Congé d'urgence"),
        ('other', 'Autre'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('rejected', 'Refusé'),
        ('cancelled', 'Annulé'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='leave_requests',
        verbose_name="Employé"
    )
    leave_type = models.CharField(
        max_length=20, 
        choices=LEAVE_TYPE_CHOICES,
        verbose_name="Type de congé"
    )
    start_date = models.DateField(verbose_name="Date de début")
    end_date = models.DateField(verbose_name="Date de fin")
    total_days = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Nombre de jours"
    )
    reason = models.TextField(verbose_name="Raison")
    supporting_documents = models.JSONField(
        default=list,
        help_text="Documents justificatifs",
        verbose_name="Documents justificatifs"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Statut"
    )
    reviewed_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leave_requests_reviewed',
        verbose_name="Révisé par"
    )
    reviewed_at = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Date de révision"
    )
    review_notes = models.TextField(
        blank=True,
        verbose_name="Notes de révision"
    )
    replacement_arranged = models.BooleanField(
        default=False,
        verbose_name="Remplacement organisé"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'hr_leave_requests'
        ordering = ['-created_at']
        verbose_name = "Demande de congé"
        verbose_name_plural = "Demandes de congés"
        indexes = [
            models.Index(fields=['employee', 'status']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.get_leave_type_display()} ({self.start_date} to {self.end_date})"



class AbsenceRecord(models.Model):
    """Enregistrement des absences"""
    ABSENCE_TYPE_CHOICES = [
        ('authorized', 'Absence autorisée'),
        ('unauthorized', 'Absence non autorisée'),
        ('late', 'Retard'),
        ('early_departure', 'Départ anticipé'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='absences',
        verbose_name="Employé"
    )
    date = models.DateField(verbose_name="Date")
    absence_type = models.CharField(
        max_length=20, 
        choices=ABSENCE_TYPE_CHOICES,
        verbose_name="Type d'absence"
    )
    scheduled_start = models.TimeField(verbose_name="Heure prévue de début")
    actual_start = models.TimeField(
        null=True, 
        blank=True,
        verbose_name="Heure réelle de début"
    )
    scheduled_end = models.TimeField(verbose_name="Heure prévue de fin")
    actual_end = models.TimeField(
        null=True, 
        blank=True,
        verbose_name="Heure réelle de fin"
    )
    duration_minutes = models.IntegerField(
        default=0,
        help_text="Durée de l'absence/retard en minutes",
        verbose_name="Durée (minutes)"
    )
    reason = models.TextField(blank=True, verbose_name="Raison")
    is_justified = models.BooleanField(
        default=False,
        verbose_name="Justifié"
    )
    justification = models.TextField(
        blank=True,
        verbose_name="Justification"
    )
    justification_documents = models.JSONField(
        default=list,
        verbose_name="Documents justificatifs"
    )
    reported_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        related_name='absences_reported',
        verbose_name="Signalé par"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'hr_absence_records'
        ordering = ['-date']
        verbose_name = "Enregistrement d'absence"
        verbose_name_plural = "Enregistrements d'absences"
        indexes = [
            models.Index(fields=['employee', '-date']),
            models.Index(fields=['absence_type', 'is_justified']),
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.get_absence_type_display()} ({self.date})"



class ReplacementRequest(models.Model):
    """Demandes de remplacement"""
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('rejected', 'Refusé'),
        ('completed', 'Terminé'),
        ('cancelled', 'Annulé'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requesting_employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='replacement_requests_made',
        verbose_name="Employé demandeur"
    )
    replacement_employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replacement_requests_received',
        verbose_name="Employé remplaçant"
    )
    date = models.DateField(verbose_name="Date")
    start_time = models.TimeField(verbose_name="Heure de début")
    end_time = models.TimeField(verbose_name="Heure de fin")
    reason = models.TextField(verbose_name="Raison")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Statut"
    )
    approved_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replacements_approved',
        verbose_name="Approuvé par"
    )
    approved_at = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Date d'approbation"
    )
    notes = models.TextField(blank=True, verbose_name="Notes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'hr_replacement_requests'
        ordering = ['-created_at']
        verbose_name = "Demande de remplacement"
        verbose_name_plural = "Demandes de remplacement"
        indexes = [
            models.Index(fields=['requesting_employee', 'status']),
            models.Index(fields=['replacement_employee', 'status']),
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        replacement_name = self.replacement_employee.get_full_name() if self.replacement_employee else "Non assigné"
        return f"{self.requesting_employee.get_full_name()} → {replacement_name} ({self.date})"


