from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from gestion_compte.models import Utilisateur, Pharmacie
from decimal import Decimal
import uuid
from django.utils import timezone

# Create your models here.

# ============================================================================
# MODÈLES DE MESSAGERIE
# ============================================================================

class Conversation(models.Model):
    """Modèle pour les conversations entre utilisateurs"""
    CONVERSATION_TYPE_CHOICES = [
        ('private', 'Privée'),
        ('group', 'Groupe'),
        ('channel', 'Canal'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation_type = models.CharField(
        max_length=20,
        choices=CONVERSATION_TYPE_CHOICES,
        default='private',
        verbose_name="Type de conversation"
    )
    name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Nom du groupe ou canal (optionnel pour conversations privées)",
        verbose_name="Nom"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description"
    )
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='conversations',
        null=True,
        blank=True,
        help_text="Pharmacie associée (pour les groupes/canaux)",
        verbose_name="Pharmacie"
    )
    participants = models.ManyToManyField(
        Utilisateur,
        through='ConversationParticipant',
        related_name='conversations',
        verbose_name="Participants"
    )
    created_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        related_name='conversations_created',
        verbose_name="Créé par"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active"
    )
    is_archived = models.BooleanField(
        default=False,
        verbose_name="Archivée"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'comm_conversations'
        ordering = ['-updated_at']
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"
        indexes = [
            models.Index(fields=['conversation_type', 'is_active']),
            models.Index(fields=['pharmacie', '-updated_at']),
        ]
    
    def __str__(self):
        if self.name:
            return self.name
        # Pour les conversations privées, afficher les participants
        participants = self.participants.all()[:2]
        return f"Conversation: {', '.join([p.get_full_name() for p in participants])}"
    
    def get_last_message(self):
        """Retourne le dernier message de la conversation"""
        return self.messages.order_by('-created_at').first()


class ConversationParticipant(models.Model):
    """Modèle intermédiaire pour gérer les participants d'une conversation"""
    ROLE_CHOICES = [
        ('member', 'Membre'),
        ('admin', 'Administrateur'),
        ('moderator', 'Modérateur'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='conversation_participants',
        verbose_name="Conversation"
    )
    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='conversation_memberships',
        verbose_name="Utilisateur"
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='member',
        verbose_name="Rôle"
    )
    is_muted = models.BooleanField(
        default=False,
        verbose_name="Notifications désactivées"
    )
    last_read_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Dernière lecture"
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'comm_conversation_participants'
        unique_together = [['conversation', 'utilisateur']]
        verbose_name = "Participant"
        verbose_name_plural = "Participants"
        indexes = [
            models.Index(fields=['utilisateur', '-joined_at']),
        ]
    
    def __str__(self):
        return f"{self.utilisateur.get_full_name()} dans {self.conversation}"
    
    def get_unread_count(self):
        """Compte les messages non lus"""
        if not self.last_read_at:
            return self.conversation.messages.count()
        return self.conversation.messages.filter(
            created_at__gt=self.last_read_at
        ).exclude(sender=self.utilisateur).count()


class Message(models.Model):
    """Modèle pour les messages"""
    MESSAGE_TYPE_CHOICES = [
        ('text', 'Texte'),
        ('image', 'Image'),
        ('file', 'Fichier'),
        ('prescription', 'Ordonnance'),
        ('system', 'Système'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Basse'),
        ('normal', 'Normale'),
        ('high', 'Haute'),
        ('urgent', 'Urgente'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name="Conversation"
    )
    sender = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='messages_sent',
        verbose_name="Expéditeur"
    )
    message_type = models.CharField(
        max_length=20,
        choices=MESSAGE_TYPE_CHOICES,
        default='text',
        verbose_name="Type de message"
    )
    content = models.TextField(
        verbose_name="Contenu"
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='normal',
        verbose_name="Priorité"
    )
    is_encrypted = models.BooleanField(
        default=True,
        verbose_name="Chiffré"
    )
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name="Réponse à"
    )
    is_edited = models.BooleanField(
        default=False,
        verbose_name="Modifié"
    )
    edited_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Modifié le"
    )
    is_deleted = models.BooleanField(
        default=False,
        verbose_name="Supprimé"
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Supprimé le"
    )
    metadata = models.JSONField(
        default=dict,
        help_text="Métadonnées supplémentaires (traduction, suggestions IA, etc.)",
        verbose_name="Métadonnées"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'comm_messages'
        ordering = ['created_at']
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['sender', '-created_at']),
            models.Index(fields=['priority', '-created_at']),
        ]
    
    def __str__(self):
        return f"Message de {self.sender.get_full_name()} dans {self.conversation}"


class MessageAttachment(models.Model):
    """Pièces jointes aux messages"""
    ATTACHMENT_TYPE_CHOICES = [
        ('image', 'Image'),
        ('document', 'Document'),
        ('prescription', 'Ordonnance'),
        ('other', 'Autre'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name="Message"
    )
    attachment_type = models.CharField(
        max_length=20,
        choices=ATTACHMENT_TYPE_CHOICES,
        verbose_name="Type de pièce jointe"
    )
    file = models.FileField(
        upload_to='messages/attachments/%Y/%m/%d/',
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx', 'txt']
            )
        ],
        verbose_name="Fichier"
    )
    file_name = models.CharField(
        max_length=255,
        verbose_name="Nom du fichier"
    )
    file_size = models.IntegerField(
        help_text="Taille en octets",
        verbose_name="Taille du fichier"
    )
    mime_type = models.CharField(
        max_length=100,
        verbose_name="Type MIME"
    )
    thumbnail = models.ImageField(
        upload_to='messages/thumbnails/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name="Miniature"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'comm_message_attachments'
        ordering = ['created_at']
        verbose_name = "Pièce jointe"
        verbose_name_plural = "Pièces jointes"
    
    def __str__(self):
        return f"{self.file_name} ({self.get_attachment_type_display()})"

class MessageReadReceipt(models.Model):
    """Accusés de lecture des messages"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='read_receipts',
        verbose_name="Message"
    )
    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='message_reads',
        verbose_name="Utilisateur"
    )
    read_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'comm_message_read_receipts'
        unique_together = [['message', 'utilisateur']]
        verbose_name = "Accusé de lecture"
        verbose_name_plural = "Accusés de lecture"
        indexes = [
            models.Index(fields=['message', 'read_at']),
        ]
    
    def __str__(self):
        return f"{self.utilisateur.get_full_name()} a lu le message à {self.read_at}"

# ============================================================================
# MODÈLES POUR LE DOSSIER MÉDICAL
# ============================================================================

class PatientMedicalRecord(models.Model):
    """Dossier médical numérique du patient"""
    BLOOD_TYPE_CHOICES = [
        ('A+', 'A+'),
        ('A-', 'A-'),
        ('B+', 'B+'),
        ('B-', 'B-'),
        ('AB+', 'AB+'),
        ('AB-', 'AB-'),
        ('O+', 'O+'),
        ('O-', 'O-'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.OneToOneField(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='medical_record',
        verbose_name="Patient"
    )
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='patient_records',
        verbose_name="Pharmacie principale"
    )
    medical_record_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Numéro de dossier médical"
    )
    blood_type = models.CharField(
        max_length=3,
        choices=BLOOD_TYPE_CHOICES,
        blank=True,
        verbose_name="Groupe sanguin"
    )
    allergies = models.JSONField(
        default=list,
        help_text="Liste des allergies connues",
        verbose_name="Allergies"
    )
    chronic_conditions = models.JSONField(
        default=list,
        help_text="Liste des pathologies chroniques",
        verbose_name="Pathologies chroniques"
    )
    current_medications = models.JSONField(
        default=list,
        help_text="Médicaments actuels",
        verbose_name="Médicaments actuels"
    )
    emergency_contact = models.JSONField(
        default=dict,
        help_text="Contact d'urgence {nom, téléphone, relation}",
        verbose_name="Contact d'urgence"
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notes médicales"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Actif"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'comm_patient_medical_records'
        ordering = ['-created_at']
        verbose_name = "Dossier médical"
        verbose_name_plural = "Dossiers médicaux"
        indexes = [
            models.Index(fields=['patient']),
            models.Index(fields=['medical_record_number']),
            models.Index(fields=['pharmacie', 'is_active']),
        ]
    
    def __str__(self):
        return f"Dossier médical de {self.patient.get_full_name()} - {self.medical_record_number}"


class Prescription(models.Model):
    """Ordonnances médicales"""
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('validated', 'Validée'),
        ('dispensed', 'Délivrée'),
        ('partially_dispensed', 'Partiellement délivrée'),
        ('expired', 'Expirée'),
        ('cancelled', 'Annulée'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    medical_record = models.ForeignKey(
        PatientMedicalRecord,
        on_delete=models.CASCADE,
        related_name='prescriptions',
        verbose_name="Dossier médical"
    )
    prescription_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Numéro d'ordonnance"
    )
    prescriber_name = models.CharField(
        max_length=255,
        verbose_name="Nom du prescripteur"
    )
    prescriber_license = models.CharField(
        max_length=100,
        verbose_name="Numéro de licence du prescripteur"
    )
    prescription_date = models.DateField(
        verbose_name="Date de prescription"
    )
    expiry_date = models.DateField(
        verbose_name="Date d'expiration"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Statut"
    )
    is_renewable = models.BooleanField(
        default=False,
        verbose_name="Renouvelable"
    )
    renewal_count = models.IntegerField(
        default=0,
        verbose_name="Nombre de renouvellements"
    )
    max_renewals = models.IntegerField(
        default=0,
        verbose_name="Renouvellements maximum"
    )
    scan_document = models.FileField(
        upload_to='prescriptions/%Y/%m/%d/',
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])
        ],
        verbose_name="Scan de l'ordonnance"
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notes"
    )
    validated_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='validated_prescriptions',
        verbose_name="Validé par"
    )
    validated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Validé le"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'comm_prescriptions'
        ordering = ['-prescription_date']
        verbose_name = "Ordonnance"
        verbose_name_plural = "Ordonnances"
        indexes = [
            models.Index(fields=['medical_record', '-prescription_date']),
            models.Index(fields=['prescription_number']),
            models.Index(fields=['status', '-prescription_date']),
            models.Index(fields=['expiry_date']),
        ]
    
    def __str__(self):
        return f"Ordonnance {self.prescription_number} - {self.medical_record.patient.get_full_name()}"
    
    def is_expired(self):
        """Vérifie si l'ordonnance est expirée"""
        return timezone.now().date() > self.expiry_date
    
    def can_be_renewed(self):
        """Vérifie si l'ordonnance peut être renouvelée"""
        return self.is_renewable and self.renewal_count < self.max_renewals


class PrescriptionItem(models.Model):
    """Lignes d'ordonnance (médicaments prescrits)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Ordonnance"
    )
    medication_name = models.CharField(
        max_length=255,
        verbose_name="Nom du médicament"
    )
    dosage = models.CharField(
        max_length=100,
        verbose_name="Dosage"
    )
    form = models.CharField(
        max_length=100,
        help_text="Forme galénique (comprimé, sirop, etc.)",
        verbose_name="Forme"
    )
    quantity = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Quantité"
    )
    frequency = models.CharField(
        max_length=255,
        help_text="Fréquence de prise (ex: 3 fois par jour)",
        verbose_name="Fréquence"
    )
    duration_days = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Durée du traitement en jours",
        verbose_name="Durée (jours)"
    )
    instructions = models.TextField(
        blank=True,
        verbose_name="Instructions particulières"
    )
    quantity_dispensed = models.IntegerField(
        default=0,
        verbose_name="Quantité délivrée"
    )
    is_substitutable = models.BooleanField(
        default=True,
        verbose_name="Substituable"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'comm_prescription_items'
        ordering = ['created_at']
        verbose_name = "Ligne d'ordonnance"
        verbose_name_plural = "Lignes d'ordonnances"
    
    def __str__(self):
        return f"{self.medication_name} - {self.dosage} ({self.quantity})"
    
class MedicationHistory(models.Model):
    """Historique des médicaments achetés/délivrés"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    medical_record = models.ForeignKey(
        PatientMedicalRecord,
        on_delete=models.CASCADE,
        related_name='medication_history',
        verbose_name="Dossier médical"
    )
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dispensing_history',
        verbose_name="Ordonnance"
    )
    medication_name = models.CharField(
        max_length=255,
        verbose_name="Nom du médicament"
    )
    dosage = models.CharField(
        max_length=100,
        verbose_name="Dosage"
    )
    quantity = models.IntegerField(
        verbose_name="Quantité"
    )
    dispensed_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        related_name='medications_dispensed',
        verbose_name="Délivré par"
    )
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='medication_history',
        verbose_name="Pharmacie"
    )
    dispensed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Délivré le"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Prix"
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notes"
    )
    
    class Meta:
        db_table = 'comm_medication_history'
        ordering = ['-dispensed_at']
        verbose_name = "Historique de médicament"
        verbose_name_plural = "Historiques de médicaments"
        indexes = [
            models.Index(fields=['medical_record', '-dispensed_at']),
            models.Index(fields=['pharmacie', '-dispensed_at']),
            models.Index(fields=['medication_name']),
        ]
    
    def __str__(self):
        return f"{self.medication_name} - {self.medical_record.patient.get_full_name()} ({self.dispensed_at.date()})"

class DrugInteractionAlert(models.Model):
    """Alertes d'interactions médicamenteuses"""
    SEVERITY_CHOICES = [
        ('minor', 'Mineure'),
        ('moderate', 'Modérée'),
        ('major', 'Majeure'),
        ('contraindicated', 'Contre-indiqué'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    medical_record = models.ForeignKey(
        PatientMedicalRecord,
        on_delete=models.CASCADE,
        related_name='drug_interaction_alerts',
        verbose_name="Dossier médical"
    )
    medication_a = models.CharField(
        max_length=255,
        verbose_name="Médicament A"
    )
    medication_b = models.CharField(
        max_length=255,
        verbose_name="Médicament B"
    )
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        verbose_name="Sévérité"
    )
    description = models.TextField(
        verbose_name="Description de l'interaction"
    )
    recommendations = models.TextField(
        verbose_name="Recommandations"
    )
    is_acknowledged = models.BooleanField(
        default=False,
        verbose_name="Pris en compte"
    )
    acknowledged_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='drug_alerts_acknowledged',
        verbose_name="Pris en compte par"
    )
    acknowledged_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Pris en compte le"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'comm_drug_interaction_alerts'
        ordering = ['-created_at']
        verbose_name = "Alerte d'interaction médicamenteuse"
        verbose_name_plural = "Alertes d'interactions médicamenteuses"
        indexes = [
            models.Index(fields=['medical_record', '-created_at']),
            models.Index(fields=['severity', 'is_acknowledged']),
        ]
    
    def __str__(self):
        return f"Interaction {self.medication_a} / {self.medication_b} - {self.get_severity_display()}"



# ============================================================================
# MODÈLES DE NOTIFICATIONS
# ============================================================================

class Notification(models.Model):
    """Système de notifications intelligentes"""
    NOTIFICATION_TYPE_CHOICES = [
        ('prescription_pending', 'Ordonnance en attente'),
        ('prescription_ready', 'Ordonnance prête'),
        ('prescription_expiring', 'Ordonnance expirant bientôt'),
        ('stock_low', 'Stock faible'),
        ('stock_out', 'Rupture de stock'),
        ('medication_reminder', 'Rappel de prise de médicament'),
        ('leave_request', 'Demande de congé'),
        ('message', 'Nouveau message'),
        ('drug_interaction', 'Interaction médicamenteuse'),
        ('appointment', 'Rendez-vous'),
        ('system', 'Système'),
        ('other', 'Autre'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Basse'),
        ('normal', 'Normale'),
        ('high', 'Haute'),
        ('urgent', 'Urgente'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('sent', 'Envoyée'),
        ('delivered', 'Délivrée'),
        ('read', 'Lue'),
        ('failed', 'Échec'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='notifications_received',
        verbose_name="Destinataire"
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPE_CHOICES,
        verbose_name="Type de notification"
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='normal',
        verbose_name="Priorité"
    )
    title = models.CharField(
        max_length=255,
        verbose_name="Titre"
    )
    message = models.TextField(
        verbose_name="Message"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Statut"
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name="Lue"
    )
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Lue le"
    )
    # Canaux de diffusion
    send_in_app = models.BooleanField(
        default=True,
        verbose_name="Envoyer dans l'application"
    )
    send_email = models.BooleanField(
        default=False,
        verbose_name="Envoyer par email"
    )
    send_sms = models.BooleanField(
        default=False,
        verbose_name="Envoyer par SMS"
    )
    # Métadonnées
    data = models.JSONField(
        default=dict,
        help_text="Données supplémentaires (liens, actions, etc.)",
        verbose_name="Données"
    )
    related_object_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Type d'objet lié (ex: prescription, message)",
        verbose_name="Type d'objet lié"
    )
    related_object_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name="ID de l'objet lié"
    )
    # Dates
    scheduled_for = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Pour les notifications programmées",
        verbose_name="Programmée pour"
    )
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Envoyée le"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'comm_notifications'
        ordering = ['-created_at']
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['status', 'scheduled_for']),
            models.Index(fields=['priority', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_notification_type_display()} pour {self.recipient.get_full_name()}"


class NotificationPreference(models.Model):
    """Préférences de notification par utilisateur"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.OneToOneField(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        verbose_name="Utilisateur"
    )
    # Préférences globales
    enable_in_app = models.BooleanField(
        default=True,
        verbose_name="Notifications dans l'app"
    )
    enable_email = models.BooleanField(
        default=True,
        verbose_name="Notifications par email"
    )
    enable_sms = models.BooleanField(
        default=False,
        verbose_name="Notifications par SMS"
    )
    # Préférences par type
    preferences = models.JSONField(
        default=dict,
        help_text="Préférences détaillées par type de notification",
        verbose_name="Préférences détaillées"
    )
    # Plages horaires
    quiet_hours_start = models.TimeField(
        null=True,
        blank=True,
        help_text="Début de la période sans notification",
        verbose_name="Début période silencieuse"
    )
    quiet_hours_end = models.TimeField(
        null=True,
        blank=True,
        help_text="Fin de la période sans notification",
        verbose_name="Fin période silencieuse"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'comm_notification_preferences'
        verbose_name = "Préférence de notification"
        verbose_name_plural = "Préférences de notifications"
    
    def __str__(self):
        return f"Préférences de {self.utilisateur.get_full_name()}"


# ============================================================================
# MODÈLES POUR LES CANAUX DE COMMUNICATION
# ============================================================================

class Channel(models.Model):
    """Canaux thématiques pour la communication de groupe"""
    CHANNEL_TYPE_CHOICES = [
        ('urgent', 'Urgent'),
        ('stock', 'Stock'),
        ('security', 'Sécurité'),
        ('news', 'Nouveautés'),
        ('general', 'Général'),
        ('custom', 'Personnalisé'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='channels',
        verbose_name="Pharmacie"
    )
    name = models.CharField(
        max_length=255,
        verbose_name="Nom"
    )
    channel_type = models.CharField(
        max_length=20,
        choices=CHANNEL_TYPE_CHOICES,
        verbose_name="Type de canal"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description"
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="Nom de l'icône ou emoji",
        verbose_name="Icône"
    )
    color = models.CharField(
        max_length=7,
        default='#3498db',
        help_text="Couleur hexadécimale",
        verbose_name="Couleur"
    )
    is_private = models.BooleanField(
        default=False,
        help_text="Si privé, nécessite une invitation",
        verbose_name="Privé"
    )
    is_archived = models.BooleanField(
        default=False,
        verbose_name="Archivé"
    )
    created_by = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        related_name='channels_created',
        verbose_name="Créé par"
    )
    members = models.ManyToManyField(
        Utilisateur,
        through='ChannelMembership',
        related_name='channels_member',
        verbose_name="Membres"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'comm_channels'
        ordering = ['channel_type', 'name']
        unique_together = [['pharmacie', 'name']]
        verbose_name = "Canal"
        verbose_name_plural = "Canaux"
        indexes = [
            models.Index(fields=['pharmacie', 'is_archived']),
            models.Index(fields=['channel_type']),
        ]
    
    def __str__(self):
        return f"#{self.name} ({self.pharmacie.nom})"


class ChannelMembership(models.Model):
    """Adhésion aux canaux"""
    ROLE_CHOICES = [
        ('member', 'Membre'),
        ('moderator', 'Modérateur'),
        ('admin', 'Administrateur'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    channel = models.ForeignKey(
        Channel,
        on_delete=models.CASCADE,
        related_name='memberships',
        verbose_name="Canal"
    )
    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='channel_memberships',
        verbose_name="Utilisateur"
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='member',
        verbose_name="Rôle"
    )
    is_muted = models.BooleanField(
        default=False,
        verbose_name="Notifications désactivées"
    )
    last_read_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Dernière lecture"
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'comm_channel_memberships'
        unique_together = [['channel', 'utilisateur']]
        verbose_name = "Adhésion au canal"
        verbose_name_plural = "Adhésions aux canaux"
    
    def __str__(self):
        return f"{self.utilisateur.get_full_name()} dans #{self.channel.name}"

class ChannelPost(models.Model):
    """Publications dans les canaux"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    channel = models.ForeignKey(
        Channel,
        on_delete=models.CASCADE,
        related_name='posts',
        verbose_name="Canal"
    )
    author = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='channel_posts',
        verbose_name="Auteur"
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Titre"
    )
    content = models.TextField(
        verbose_name="Contenu"
    )
    is_pinned = models.BooleanField(
        default=False,
        help_text="Épingler en haut du canal",
        verbose_name="Épinglé"
    )
    is_announcement = models.BooleanField(
        default=False,
        verbose_name="Annonce"
    )
    attachments = models.JSONField(
        default=list,
        help_text="Liste des fichiers joints",
        verbose_name="Pièces jointes"
    )
    tags = models.JSONField(
        default=list,
        help_text="Tags pour catégoriser",
        verbose_name="Tags"
    )
    is_deleted = models.BooleanField(
        default=False,
        verbose_name="Supprimé"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'comm_channel_posts'
        ordering = ['-is_pinned', '-created_at']
        verbose_name = "Publication de canal"
        verbose_name_plural = "Publications de canaux"
        indexes = [
            models.Index(fields=['channel', '-created_at']),
            models.Index(fields=['author', '-created_at']),
            models.Index(fields=['is_pinned', '-created_at']),
        ]
    
    def __str__(self):
        return f"Post dans #{self.channel.name} par {self.author.get_full_name()}"


# ============================================================================
# MODÈLES POUR L'ASSISTANCE EN LIGNE ET CHATBOT
# ============================================================================

class OnlineConsultation(models.Model):
    """Demandes de conseil en ligne"""
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('in_progress', 'En cours'),
        ('answered', 'Répondue'),
        ('closed', 'Clôturée'),
        ('cancelled', 'Annulée'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='consultations_requested',
        verbose_name="Patient"
    )
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='consultations',
        verbose_name="Pharmacie"
    )
    access_code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Code sécurisé fourni au patient",
        verbose_name="Code d'accès"
    )
    subject = models.CharField(
        max_length=255,
        verbose_name="Sujet"
    )
    question = models.TextField(
        verbose_name="Question"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Statut"
    )
    assigned_to = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='consultations_assigned',
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
    attachments = models.JSONField(
        default=list,
        help_text="Photos d'ordonnances, documents, etc.",
        verbose_name="Pièces jointes"
    )
    is_urgent = models.BooleanField(
        default=False,
        verbose_name="Urgent"
    )
    rating = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MinValueValidator(5)],
        help_text="Note de satisfaction (1-5)",
        verbose_name="Note"
    )
    feedback = models.TextField(
        blank=True,
        verbose_name="Commentaire"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'comm_online_consultations'
        ordering = ['-created_at']
        verbose_name = "Consultation en ligne"
        verbose_name_plural = "Consultations en ligne"
        indexes = [
            models.Index(fields=['patient', '-created_at']),
            models.Index(fields=['pharmacie', 'status']),
            models.Index(fields=['access_code']),
            models.Index(fields=['is_urgent', '-created_at']),
        ]
    
    def __str__(self):
        return f"Consultation #{self.access_code} - {self.subject}"

class ChatbotConversation(models.Model):
    """Conversations avec le chatbot IA"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='chatbot_conversations',
        null=True,
        blank=True,
        help_text="Null si utilisateur anonyme",
        verbose_name="Utilisateur"
    )
    session_id = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="ID de session"
    )
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='chatbot_conversations',
        null=True,
        blank=True,
        verbose_name="Pharmacie"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active"
    )
    context = models.JSONField(
        default=dict,
        help_text="Contexte de la conversation",
        verbose_name="Contexte"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'comm_chatbot_conversations'
        ordering = ['-last_activity']
        verbose_name = "Conversation chatbot"
        verbose_name_plural = "Conversations chatbot"
        indexes = [
            models.Index(fields=['utilisateur', '-last_activity']),
            models.Index(fields=['session_id']),
        ]
    
    def __str__(self):
        user_name = self.utilisateur.get_full_name() if self.utilisateur else "Anonyme"
        return f"Conversation chatbot - {user_name} ({self.session_id})"


class ChatbotMessage(models.Model):
    """Messages échangés avec le chatbot"""
    SENDER_CHOICES = [
        ('user', 'Utilisateur'),
        ('bot', 'Chatbot'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        ChatbotConversation,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name="Conversation"
    )
    sender = models.CharField(
        max_length=10,
        choices=SENDER_CHOICES,
        verbose_name="Expéditeur"
    )
    message = models.TextField(
        verbose_name="Message"
    )
    intent = models.CharField(
        max_length=100,
        blank=True,
        help_text="Intention détectée par l'IA",
        verbose_name="Intention"
    )
    confidence = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Confiance de l'IA (0-100%)",
        verbose_name="Confiance"
    )
    suggested_responses = models.JSONField(
        default=list,
        help_text="Réponses suggérées par l'IA",
        verbose_name="Réponses suggérées"
    )
    metadata = models.JSONField(
        default=dict,
        verbose_name="Métadonnées"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'comm_chatbot_messages'
        ordering = ['created_at']
        verbose_name = "Message chatbot"
        verbose_name_plural = "Messages chatbot"
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_sender_display()}: {self.message[:50]}..."



# ============================================================================
# MODÈLES POUR L'ARCHIVAGE ET LA TRAÇABILITÉ
# ============================================================================

class CommunicationArchive(models.Model):
    """Archivage des communications"""
    ARCHIVE_TYPE_CHOICES = [
        ('message', 'Message'),
        ('consultation', 'Consultation'),
        ('prescription', 'Ordonnance'),
        ('channel_post', 'Publication de canal'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    archive_type = models.CharField(
        max_length=20,
        choices=ARCHIVE_TYPE_CHOICES,
        verbose_name="Type"
    )
    original_object_id = models.UUIDField(
        verbose_name="ID de l'objet original"
    )
    pharmacie = models.ForeignKey(
        Pharmacie,
        on_delete=models.CASCADE,
        related_name='communication_archives',
        verbose_name="Pharmacie"
    )
    data = models.JSONField(
        help_text="Données complètes de l'objet archivé",
        verbose_name="Données"
    )
    participants = models.JSONField(
        default=list,
        help_text="Liste des participants (IDs et noms)",
        verbose_name="Participants"
    )
    archived_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'comm_archives'
        ordering = ['-archived_at']
        verbose_name = "Archive de communication"
        verbose_name_plural = "Archives de communications"
        indexes = [
            models.Index(fields=['pharmacie', '-archived_at']),
            models.Index(fields=['archive_type', '-archived_at']),
            models.Index(fields=['original_object_id']),
        ]
    
    def __str__(self):
        return f"Archive {self.get_archive_type_display()} - {self.archived_at.date()}"

class AccessLog(models.Model):
    """Journal d'audit des accès"""
    ACTION_CHOICES = [
        ('view', 'Consultation'),
        ('create', 'Création'),
        ('update', 'Modification'),
        ('delete', 'Suppression'),
        ('export', 'Export'),
        ('share', 'Partage'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='access_logs',
        verbose_name="Utilisateur"
    )
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        verbose_name="Action"
    )
    resource_type = models.CharField(
        max_length=50,
        help_text="Type de ressource (message, prescription, etc.)",
        verbose_name="Type de ressource"
    )
    resource_id = models.UUIDField(
        verbose_name="ID de la ressource"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="Adresse IP"
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name="User agent"
    )
    details = models.JSONField(
        default=dict,
        help_text="Détails supplémentaires",
        verbose_name="Détails"
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'comm_access_logs'
        ordering = ['-timestamp']
        verbose_name = "Journal d'accès"
        verbose_name_plural = "Journaux d'accès"
        indexes = [
            models.Index(fields=['utilisateur', '-timestamp']),
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['action', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.utilisateur.get_full_name()} - {self.get_action_display()} {self.resource_type} ({self.timestamp})"


class UserPresence(models.Model):
    """Suivi de la présence en ligne des utilisateurs"""
    STATUS_CHOICES = [
        ('online', 'En ligne'),
        ('away', 'Absent'),
        ('busy', 'Occupé'),
        ('offline', 'Hors ligne'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.OneToOneField(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='presence',
        verbose_name="Utilisateur"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='offline',
        verbose_name="Statut"
    )
    custom_message = models.CharField(
        max_length=255,
        blank=True,
        help_text="Message de statut personnalisé",
        verbose_name="Message personnalisé"
    )
    last_seen = models.DateTimeField(
        auto_now=True,
        verbose_name="Dernière activité"
    )
    
    class Meta:
        db_table = 'comm_user_presence'
        verbose_name = "Présence utilisateur"
        verbose_name_plural = "Présences utilisateurs"
        indexes = [
            models.Index(fields=['status', 'last_seen']),
        ]
    
    def __str__(self):
        return f"{self.utilisateur.get_full_name()} - {self.get_status_display()}"


