"""
Signals pour automatiser les processus de communication
"""
from django.db.models.signals import post_save, pre_save, m2m_changed
from django.dispatch import receiver
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
import secrets
import string
from datetime import datetime, timedelta

from .models import (
    Message, MessageReadReceipt, Conversation, ConversationParticipant,
    Prescription, MedicationHistory, DrugInteractionAlert,
    Notification, OnlineConsultation, PatientMedicalRecord,
    ChannelPost, UserPresence, CommunicationArchive, AccessLog
)


# ============================================================================
# SIGNALS MESSAGERIE
# ============================================================================

@receiver(post_save, sender=Message)
def create_message_notifications(sender, instance, created, **kwargs):
    """
    Crée des notifications pour les participants d'une conversation
    lors de l'envoi d'un nouveau message
    """
    if created and not instance.is_deleted:
        # Récupérer tous les participants sauf l'expéditeur
        participants = instance.conversation.conversation_participants.exclude(
            utilisateur=instance.sender
        )
        
        for participant in participants:
            # Ne pas notifier si l'utilisateur a mis la conversation en muet
            if not participant.is_muted:
                # Déterminer la priorité de la notification selon la priorité du message
                notification_priority = 'high' if instance.priority == 'urgent' else 'normal'
                
                Notification.objects.create(
                    recipient=participant.utilisateur,
                    notification_type='message',
                    priority=notification_priority,
                    title=f"Nouveau message de {instance.sender.get_full_name()}",
                    message=instance.content[:100] + ('...' if len(instance.content) > 100 else ''),
                    send_in_app=True,
                    send_email=instance.priority in ['high', 'urgent'],
                    send_sms=instance.priority == 'urgent',
                    data={
                        'conversation_id': str(instance.conversation.id),
                        'message_id': str(instance.id)
                    },
                    related_object_type='message',
                    related_object_id=instance.id
                )


@receiver(post_save, sender=Message)
def update_conversation_timestamp(sender, instance, created, **kwargs):
    """
    Met à jour le timestamp de la conversation lors d'un nouveau message
    """
    if created:
        instance.conversation.updated_at = timezone.now()
        instance.conversation.save(update_fields=['updated_at'])


@receiver(post_save, sender=MessageReadReceipt)
def update_participant_last_read(sender, instance, created, **kwargs):
    """
    Met à jour la dernière lecture du participant
    """
    if created:
        try:
            participant = ConversationParticipant.objects.get(
                conversation=instance.message.conversation,
                utilisateur=instance.utilisateur
            )
            participant.last_read_at = instance.read_at
            participant.save(update_fields=['last_read_at'])
        except ConversationParticipant.DoesNotExist:
            pass


@receiver(post_save, sender=Message)
def detect_urgent_message_and_prioritize(sender, instance, created, **kwargs):
    """
    Détecte les messages urgents et les priorise automatiquement
    """
    if created and instance.message_type == 'text':
        urgent_keywords = ['urgent', 'urgence', 'immédiat', 'critique', 'danger']
        content_lower = instance.content.lower()
        
        # Vérifier si le message contient des mots-clés urgents
        if any(keyword in content_lower for keyword in urgent_keywords):
            instance.priority = 'urgent'
            instance.save(update_fields=['priority'])


# ============================================================================
# SIGNALS DOSSIER MÉDICAL
# ============================================================================

@receiver(post_save, sender=PatientMedicalRecord)
def generate_medical_record_number(sender, instance, created, **kwargs):
    """
    Génère automatiquement un numéro de dossier médical unique
    """
    if created and not instance.medical_record_number:
        year = timezone.now().year
        count = PatientMedicalRecord.objects.filter(
            pharmacie=instance.pharmacie,
            created_at__year=year
        ).count()
        
        instance.medical_record_number = f"MED-{instance.pharmacie.code if hasattr(instance.pharmacie, 'code') else 'PHARM'}-{year}-{count:05d}"
        instance.save(update_fields=['medical_record_number'])


@receiver(post_save, sender=Prescription)
def generate_prescription_number(sender, instance, created, **kwargs):
    """
    Génère automatiquement un numéro d'ordonnance unique
    """
    if created and not instance.prescription_number:
        year = instance.prescription_date.year
        count = Prescription.objects.filter(
            prescription_date__year=year
        ).count()
        
        instance.prescription_number = f"ORD-{year}-{count:06d}"
        instance.save(update_fields=['prescription_number'])


@receiver(post_save, sender=Prescription)
def notify_prescription_status_change(sender, instance, created, **kwargs):
    """
    Notifie le patient des changements de statut de l'ordonnance
    """
    if not created:
        # Récupérer l'ancien statut
        old_instance = Prescription.objects.filter(pk=instance.pk).first()
        
        if old_instance and old_instance.status != instance.status:
            notification_messages = {
                'validated': 'Votre ordonnance a été validée',
                'dispensed': 'Votre ordonnance a été délivrée',
                'partially_dispensed': 'Votre ordonnance a été partiellement délivrée',
                'expired': 'Votre ordonnance a expiré',
            }
            
            if instance.status in notification_messages:
                Notification.objects.create(
                    recipient=instance.medical_record.patient,
                    notification_type='prescription_ready' if instance.status == 'dispensed' else 'prescription_pending',
                    priority='normal',
                    title=notification_messages[instance.status],
                    message=f"Ordonnance N° {instance.prescription_number}",
                    send_in_app=True,
                    send_email=True,
                    data={'prescription_id': str(instance.id)},
                    related_object_type='prescription',
                    related_object_id=instance.id
                )


@receiver(post_save, sender=Prescription)
def check_prescription_expiry(sender, instance, created, **kwargs):
    """
    Crée une notification pour les ordonnances qui expirent bientôt
    """
    if not created:
        days_until_expiry = (instance.expiry_date - timezone.now().date()).days
        
        # Notifier 7 jours avant l'expiration
        if days_until_expiry == 7:
            Notification.objects.create(
                recipient=instance.medical_record.patient,
                notification_type='prescription_expiring',
                priority='normal',
                title='Ordonnance expirant bientôt',
                message=f"Votre ordonnance N° {instance.prescription_number} expire dans 7 jours",
                send_in_app=True,
                send_email=True,
                scheduled_for=timezone.now(),
                data={'prescription_id': str(instance.id)}
            )


@receiver(post_save, sender=MedicationHistory)
def detect_drug_interactions(sender, instance, created, **kwargs):
    """
    Détecte automatiquement les interactions médicamenteuses
    """
    if created:
        # Récupérer l'historique récent du patient (30 derniers jours)
        recent_medications = MedicationHistory.objects.filter(
            medical_record=instance.medical_record,
            dispensed_at__gte=timezone.now() - timedelta(days=30)
        ).exclude(id=instance.id)
        
        # Base de données simplifiée d'interactions
        # En production, utiliser une vraie base de données d'interactions
        KNOWN_INTERACTIONS = {
            ('Aspirine', 'Warfarine'): {
                'severity': 'major',
                'description': 'Risque accru de saignement',
                'recommendations': 'Surveillance étroite de l\'INR. Envisager une alternative.'
            },
            ('Amoxicilline', 'Méthotrexate'): {
                'severity': 'moderate',
                'description': 'Diminution de l\'excrétion du méthotrexate',
                'recommendations': 'Surveiller les signes de toxicité du méthotrexate.'
            },
            # Ajouter plus d'interactions connues
        }
        
        for med in recent_medications:
            # Vérifier les interactions dans les deux sens
            interaction_key1 = (instance.medication_name, med.medication_name)
            interaction_key2 = (med.medication_name, instance.medication_name)
            
            interaction = KNOWN_INTERACTIONS.get(interaction_key1) or KNOWN_INTERACTIONS.get(interaction_key2)
            
            if interaction:
                # Créer l'alerte d'interaction
                alert = DrugInteractionAlert.objects.create(
                    medical_record=instance.medical_record,
                    medication_a=instance.medication_name,
                    medication_b=med.medication_name,
                    severity=interaction['severity'],
                    description=interaction['description'],
                    recommendations=interaction['recommendations']
                )
                
                # Notifier le personnel de la pharmacie
                Notification.objects.create(
                    recipient=instance.dispensed_by,
                    notification_type='drug_interaction',
                    priority='urgent' if interaction['severity'] in ['major', 'contraindicated'] else 'high',
                    title='⚠️ Interaction médicamenteuse détectée',
                    message=f"{instance.medication_name} / {med.medication_name} - {interaction['severity']}",
                    send_in_app=True,
                    send_email=True,
                    data={'alert_id': str(alert.id)},
                    related_object_type='drug_interaction_alert',
                    related_object_id=alert.id
                )


@receiver(post_save, sender=MedicationHistory)
def check_medication_abuse(sender, instance, created, **kwargs):
    """
    Détecte les abus potentiels de médicaments
    """
    if created:
        # Compter le nombre de fois que ce médicament a été acheté dans les 30 derniers jours
        recent_purchases = MedicationHistory.objects.filter(
            medical_record=instance.medical_record,
            medication_name=instance.medication_name,
            dispensed_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        # Si plus de 3 achats du même médicament en 30 jours
        if recent_purchases > 3:
            # Créer une alerte pour le pharmacien
            Notification.objects.create(
                recipient=instance.dispensed_by,
                notification_type='system',
                priority='high',
                title='⚠️ Alerte abus potentiel',
                message=f"Patient {instance.medical_record.patient.get_full_name()}: {recent_purchases} achats de {instance.medication_name} en 30 jours",
                send_in_app=True,
                send_email=True,
                data={
                    'patient_id': str(instance.medical_record.patient.id),
                    'medication': instance.medication_name,
                    'count': recent_purchases
                }
            )


# ============================================================================
# SIGNALS NOTIFICATIONS
# ============================================================================

@receiver(post_save, sender=Notification)
def send_notification_via_channels(sender, instance, created, **kwargs):
    """
    Envoie la notification via les canaux appropriés (email, SMS)
    """
    if created and instance.status == 'pending':
        # Vérifier les préférences de l'utilisateur
        try:
            preferences = instance.recipient.notification_preferences
        except:
            preferences = None
        
        # Vérifier l'heure silencieuse
        if preferences and preferences.quiet_hours_start and preferences.quiet_hours_end:
            current_time = timezone.now().time()
            if preferences.quiet_hours_start <= current_time <= preferences.quiet_hours_end:
                # Reporter l'envoi après l'heure silencieuse
                instance.scheduled_for = timezone.now().replace(
                    hour=preferences.quiet_hours_end.hour,
                    minute=preferences.quiet_hours_end.minute
                )
                instance.save()
                return
        
        # Envoyer par email si activé
        if instance.send_email and (not preferences or preferences.enable_email):
            try:
                send_mail(
                    subject=instance.title,
                    message=instance.message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[instance.recipient.email],
                    fail_silently=True,
                )
                instance.status = 'sent'
            except Exception as e:
                instance.status = 'failed'
        
        # Envoyer par SMS si activé (intégration à faire)
        if instance.send_sms and (not preferences or preferences.enable_sms):
            # TODO: Intégrer avec un service SMS (Twilio, etc.)
            pass
        
        instance.sent_at = timezone.now()
        instance.save(update_fields=['status', 'sent_at'])


# ============================================================================
# SIGNALS CANAUX ET ASSISTANCE
# ============================================================================

@receiver(post_save, sender=ChannelPost)
def notify_channel_members(sender, instance, created, **kwargs):
    """
    Notifie les membres d'un canal lors d'une nouvelle publication
    """
    if created and not instance.is_deleted:
        # Notifier tous les membres sauf l'auteur
        memberships = instance.channel.memberships.exclude(
            utilisateur=instance.author
        ).exclude(is_muted=True)
        
        for membership in memberships:
            priority = 'high' if instance.is_announcement else 'normal'
            
            Notification.objects.create(
                recipient=membership.utilisateur,
                notification_type='system',
                priority=priority,
                title=f"Nouvelle publication dans #{instance.channel.name}",
                message=instance.title or instance.content[:100],
                send_in_app=True,
                data={
                    'channel_id': str(instance.channel.id),
                    'post_id': str(instance.id)
                }
            )


@receiver(post_save, sender=OnlineConsultation)
def generate_consultation_access_code(sender, instance, created, **kwargs):
    """
    Génère un code d'accès sécurisé pour la consultation
    """
    if created and not instance.access_code:
        # Générer un code aléatoire de 8 caractères
        code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        instance.access_code = code
        instance.save(update_fields=['access_code'])
        
        # Envoyer le code par email au patient
        send_mail(
            subject='Code d\'accès à votre consultation en ligne',
            message=f'Votre code d\'accès sécurisé est: {code}\n\nUtilisez ce code pour accéder à votre consultation.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[instance.patient.email],
            fail_silently=True,
        )


@receiver(post_save, sender=OnlineConsultation)
def notify_consultation_status_change(sender, instance, created, **kwargs):
    """
    Notifie le patient des changements de statut de la consultation
    """
    if not created:
        if instance.status == 'answered':
            Notification.objects.create(
                recipient=instance.patient,
                notification_type='system',
                priority='normal',
                title='Réponse à votre consultation',
                message=f'Le pharmacien a répondu à votre consultation sur "{instance.subject}"',
                send_in_app=True,
                send_email=True,
                data={
                    'consultation_id': str(instance.id),
                    'access_code': instance.access_code
                }
            )


# ============================================================================
# SIGNALS PRÉSENCE ET ARCHIVAGE
# ============================================================================

@receiver(post_save, sender=Message)
def archive_old_messages(sender, instance, created, **kwargs):
    """
    Archive automatiquement les messages de plus de 90 jours
    """
    if created:
        # Archiver les vieux messages (exécuter périodiquement avec Celery)
        old_date = timezone.now() - timedelta(days=90)
        old_messages = Message.objects.filter(
            created_at__lt=old_date,
            conversation__pharmacie=instance.conversation.pharmacie
        ).exclude(id=instance.id)
        
        for old_message in old_messages[:100]:  # Limiter pour éviter la surcharge
            # Créer une archive
            CommunicationArchive.objects.create(
                archive_type='message',
                original_object_id=old_message.id,
                pharmacie=old_message.conversation.pharmacie,
                data={
                    'content': old_message.content,
                    'sender': old_message.sender.get_full_name(),
                    'conversation': str(old_message.conversation.id),
                    'created_at': old_message.created_at.isoformat()
                },
                participants=[
                    {
                        'id': str(p.utilisateur.id),
                        'name': p.utilisateur.get_full_name()
                    }
                    for p in old_message.conversation.conversation_participants.all()
                ]
            )


@receiver(post_save, sender=AccessLog)
def detect_suspicious_access(sender, instance, created, **kwargs):
    """
    Détecte les accès suspects aux dossiers
    """
    if created:
        # Compter les accès récents du même utilisateur
        recent_accesses = AccessLog.objects.filter(
            utilisateur=instance.utilisateur,
            resource_type=instance.resource_type,
            timestamp__gte=timezone.now() - timedelta(minutes=5)
        ).count()
        
        # Si plus de 20 accès en 5 minutes, créer une alerte
        if recent_accesses > 20:
            # Notifier l'administrateur
            # TODO: Implémenter la notification admin
            pass


# Signal pour mettre à jour la présence automatiquement
# Ce signal devrait être appelé lors des requêtes API
def update_user_presence(utilisateur, status='online'):
    """
    Met à jour le statut de présence de l'utilisateur
    """
    UserPresence.objects.update_or_create(
        utilisateur=utilisateur,
        defaults={'status': status}
    )





