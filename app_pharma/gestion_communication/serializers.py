

"""
Serializers pour les modèles de communication
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Conversation, ConversationParticipant, Message, MessageAttachment,
    MessageReadReceipt, PatientMedicalRecord, Prescription, PrescriptionItem,
    MedicationHistory, DrugInteractionAlert, Notification, NotificationPreference,
    Channel, ChannelMembership, ChannelPost, OnlineConsultation,
    ChatbotConversation, ChatbotMessage, CommunicationArchive,
    AccessLog, UserPresence
)

Utilisateur = get_user_model()


# ============================================================================
# SERIALIZERS MESSAGERIE
# ============================================================================

class UtilisateurMinimalSerializer(serializers.ModelSerializer):
    """Serializer minimal pour les références utilisateur"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Utilisateur
        fields = ['id', 'username', 'full_name', 'email']
    
    def get_full_name(self, obj):
        return obj.get_full_name()


class MessageAttachmentSerializer(serializers.ModelSerializer):
    """Serializer pour les pièces jointes"""
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = MessageAttachment
        fields = [
            'id', 'attachment_type', 'file', 'file_url', 'file_name',
            'file_size', 'mime_type', 'thumbnail', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class MessageReadReceiptSerializer(serializers.ModelSerializer):
    """Serializer pour les accusés de lecture"""
    utilisateur_name = serializers.CharField(source='utilisateur.get_full_name', read_only=True)
    
    class Meta:
        model = MessageReadReceipt
        fields = ['id', 'message', 'utilisateur', 'utilisateur_name', 'read_at']
        read_only_fields = ['id', 'read_at']


class MessageSerializer(serializers.ModelSerializer):
    """Serializer pour les messages"""
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    sender = UtilisateurMinimalSerializer(read_only=True)
    attachments = MessageAttachmentSerializer(many=True, read_only=True)
    read_receipts = MessageReadReceiptSerializer(many=True, read_only=True)
    is_read_by_user = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'sender_name', 'message_type',
            'content', 'priority', 'is_encrypted', 'reply_to', 'attachments',
            'read_receipts', 'is_read_by_user', 'is_edited', 'edited_at',
            'is_deleted', 'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'sender', 'created_at', 'updated_at']
    
    def get_is_read_by_user(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.read_receipts.filter(utilisateur=request.user).exists()
        return False


class ConversationParticipantSerializer(serializers.ModelSerializer):
    """Serializer pour les participants"""
    utilisateur = UtilisateurMinimalSerializer(read_only=True)
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ConversationParticipant
        fields = [
            'id', 'conversation', 'utilisateur', 'role', 'is_muted',
            'last_read_at', 'unread_count', 'joined_at'
        ]
        read_only_fields = ['id', 'joined_at']
    
    def get_unread_count(self, obj):
        return obj.get_unread_count()


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer pour les conversations"""
    participants_list = ConversationParticipantSerializer(
        source='conversation_participants',
        many=True,
        read_only=True
    )
    last_message = MessageSerializer(read_only=True)
    unread_count = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'conversation_type', 'name', 'description', 'pharmacie',
            'participants_list', 'last_message', 'unread_count', 'created_by',
            'created_by_name', 'is_active', 'is_archived',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            participant = obj.conversation_participants.filter(
                utilisateur=request.user
            ).first()
            if participant:
                return participant.get_unread_count()
        return 0


# ============================================================================
# SERIALIZERS DOSSIER MÉDICAL
# ============================================================================

class PrescriptionItemSerializer(serializers.ModelSerializer):
    """Serializer pour les lignes d'ordonnance"""
    class Meta:
        model = PrescriptionItem
        fields = [
            'id', 'prescription', 'medication_name', 'dosage', 'form',
            'quantity', 'frequency', 'duration_days', 'instructions',
            'quantity_dispensed', 'is_substitutable', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PrescriptionSerializer(serializers.ModelSerializer):
    """Serializer pour les ordonnances"""
    items = PrescriptionItemSerializer(many=True, read_only=True)
    patient_name = serializers.CharField(source='medical_record.patient.get_full_name', read_only=True)
    validated_by_name = serializers.CharField(source='validated_by.get_full_name', read_only=True)
    is_expired = serializers.SerializerMethodField()
    can_be_renewed = serializers.SerializerMethodField()
    
    class Meta:
        model = Prescription
        fields = [
            'id', 'medical_record', 'patient_name', 'prescription_number',
            'prescriber_name', 'prescriber_license', 'prescription_date',
            'expiry_date', 'status', 'is_renewable', 'renewal_count',
            'max_renewals', 'scan_document', 'notes', 'validated_by',
            'validated_by_name', 'validated_at', 'items', 'is_expired',
            'can_be_renewed', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'prescription_number', 'validated_by', 'validated_at', 'created_at', 'updated_at']
    
    def get_is_expired(self, obj):
        return obj.is_expired()
    
    def get_can_be_renewed(self, obj):
        return obj.can_be_renewed()


class MedicationHistorySerializer(serializers.ModelSerializer):
    """Serializer pour l'historique des médicaments"""
    patient_name = serializers.CharField(source='medical_record.patient.get_full_name', read_only=True)
    dispensed_by_name = serializers.CharField(source='dispensed_by.get_full_name', read_only=True)
    pharmacie_name = serializers.CharField(source='pharmacie.nom', read_only=True)
    
    class Meta:
        model = MedicationHistory
        fields = [
            'id', 'medical_record', 'patient_name', 'prescription',
            'medication_name', 'dosage', 'quantity', 'dispensed_by',
            'dispensed_by_name', 'pharmacie', 'pharmacie_name',
            'dispensed_at', 'price', 'notes'
        ]
        read_only_fields = ['id', 'dispensed_at']


class DrugInteractionAlertSerializer(serializers.ModelSerializer):
    """Serializer pour les alertes d'interaction"""
    patient_name = serializers.CharField(source='medical_record.patient.get_full_name', read_only=True)
    acknowledged_by_name = serializers.CharField(source='acknowledged_by.get_full_name', read_only=True)
    
    class Meta:
        model = DrugInteractionAlert
        fields = [
            'id', 'medical_record', 'patient_name', 'medication_a',
            'medication_b', 'severity', 'description', 'recommendations',
            'is_acknowledged', 'acknowledged_by', 'acknowledged_by_name',
            'acknowledged_at', 'created_at'
        ]
        read_only_fields = ['id', 'acknowledged_by', 'acknowledged_at', 'created_at']


class PatientMedicalRecordSerializer(serializers.ModelSerializer):
    """Serializer pour les dossiers médicaux"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    pharmacie_name = serializers.CharField(source='pharmacie.nom', read_only=True)
    prescriptions = PrescriptionSerializer(many=True, read_only=True)
    medication_history = MedicationHistorySerializer(many=True, read_only=True)
    drug_interaction_alerts = DrugInteractionAlertSerializer(many=True, read_only=True)
    active_alerts_count = serializers.SerializerMethodField()
    
    class Meta:
        model = PatientMedicalRecord
        fields = [
            'id', 'patient', 'patient_name', 'pharmacie', 'pharmacie_name',
            'medical_record_number', 'blood_type', 'allergies',
            'chronic_conditions', 'current_medications', 'emergency_contact',
            'notes', 'is_active', 'prescriptions', 'medication_history',
            'drug_interaction_alerts', 'active_alerts_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'medical_record_number', 'created_at', 'updated_at']
    
    def get_active_alerts_count(self, obj):
        return obj.drug_interaction_alerts.filter(is_acknowledged=False).count()


# ============================================================================
# SERIALIZERS NOTIFICATIONS
# ============================================================================

class NotificationSerializer(serializers.ModelSerializer):
    """Serializer pour les notifications"""
    recipient_name = serializers.CharField(source='recipient.get_full_name', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'recipient_name', 'notification_type',
            'priority', 'title', 'message', 'status', 'is_read',
            'read_at', 'send_in_app', 'send_email', 'send_sms', 'data',
            'related_object_type', 'related_object_id', 'scheduled_for',
            'sent_at', 'created_at'
        ]
        read_only_fields = ['id', 'sent_at', 'created_at']


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer pour les préférences de notification"""
    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'utilisateur', 'enable_in_app', 'enable_email',
            'enable_sms', 'preferences', 'quiet_hours_start',
            'quiet_hours_end', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# SERIALIZERS CANAUX
# ============================================================================

class ChannelPostSerializer(serializers.ModelSerializer):
    """Serializer pour les publications de canaux"""
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    author = UtilisateurMinimalSerializer(read_only=True)
    
    class Meta:
        model = ChannelPost
        fields = [
            'id', 'channel', 'author', 'author_name', 'title', 'content',
            'is_pinned', 'is_announcement', 'attachments', 'tags',
            'is_deleted', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']


class ChannelMembershipSerializer(serializers.ModelSerializer):
    """Serializer pour les adhésions aux canaux"""
    utilisateur = UtilisateurMinimalSerializer(read_only=True)
    
    class Meta:
        model = ChannelMembership
        fields = [
            'id', 'channel', 'utilisateur', 'role', 'is_muted',
            'last_read_at', 'joined_at'
        ]
        read_only_fields = ['id', 'joined_at']


class ChannelSerializer(serializers.ModelSerializer):
    """Serializer pour les canaux"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    pharmacie_name = serializers.CharField(source='pharmacie.nom', read_only=True)
    memberships = ChannelMembershipSerializer(many=True, read_only=True)
    recent_posts = ChannelPostSerializer(many=True, read_only=True, source='posts')
    members_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Channel
        fields = [
            'id', 'pharmacie', 'pharmacie_name', 'name', 'channel_type',
            'description', 'icon', 'color', 'is_private', 'is_archived',
            'created_by', 'created_by_name', 'memberships', 'recent_posts',
            'members_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']
    
    def get_members_count(self, obj):
        return obj.memberships.count()


# ============================================================================
# SERIALIZERS ASSISTANCE EN LIGNE
# ============================================================================

class OnlineConsultationSerializer(serializers.ModelSerializer):
    """Serializer pour les consultations en ligne"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    pharmacie_name = serializers.CharField(source='pharmacie.nom', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    
    class Meta:
        model = OnlineConsultation
        fields = [
            'id', 'patient', 'patient_name', 'pharmacie', 'pharmacie_name',
            'access_code', 'subject', 'question', 'status', 'assigned_to',
            'assigned_to_name', 'response', 'responded_at', 'attachments',
            'is_urgent', 'rating', 'feedback', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'access_code', 'responded_at', 'created_at', 'updated_at']


class ChatbotMessageSerializer(serializers.ModelSerializer):
    """Serializer pour les messages chatbot"""
    class Meta:
        model = ChatbotMessage
        fields = [
            'id', 'conversation', 'sender', 'message', 'intent',
            'confidence', 'suggested_responses', 'metadata', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ChatbotConversationSerializer(serializers.ModelSerializer):
    """Serializer pour les conversations chatbot"""
    utilisateur_name = serializers.CharField(source='utilisateur.get_full_name', read_only=True)
    messages = ChatbotMessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = ChatbotConversation
        fields = [
            'id', 'utilisateur', 'utilisateur_name', 'session_id',
            'pharmacie', 'is_active', 'context', 'messages',
            'created_at', 'last_activity'
        ]
        read_only_fields = ['id', 'session_id', 'created_at', 'last_activity']


# ============================================================================
# SERIALIZERS ARCHIVAGE
# ============================================================================

class CommunicationArchiveSerializer(serializers.ModelSerializer):
    """Serializer pour les archives"""
    pharmacie_name = serializers.CharField(source='pharmacie.nom', read_only=True)
    
    class Meta:
        model = CommunicationArchive
        fields = [
            'id', 'archive_type', 'original_object_id', 'pharmacie',
            'pharmacie_name', 'data', 'participants', 'archived_at'
        ]
        read_only_fields = ['id', 'archived_at']


class AccessLogSerializer(serializers.ModelSerializer):
    """Serializer pour les journaux d'accès"""
    utilisateur_name = serializers.CharField(source='utilisateur.get_full_name', read_only=True)
    
    class Meta:
        model = AccessLog
        fields = [
            'id', 'utilisateur', 'utilisateur_name', 'action',
            'resource_type', 'resource_id', 'ip_address', 'user_agent',
            'details', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']


class UserPresenceSerializer(serializers.ModelSerializer):
    """Serializer pour la présence utilisateur"""
    utilisateur_name = serializers.CharField(source='utilisateur.get_full_name', read_only=True)
    
    class Meta:
        model = UserPresence
        fields = [
            'id', 'utilisateur', 'utilisateur_name', 'status',
            'custom_message', 'last_seen'
        ]
        read_only_fields = ['id', 'last_seen']


"""
Serializers pour les modèles de communication
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Conversation, ConversationParticipant, Message, MessageAttachment,
    MessageReadReceipt, PatientMedicalRecord, Prescription, PrescriptionItem,
    MedicationHistory, DrugInteractionAlert, Notification, NotificationPreference,
    Channel, ChannelMembership, ChannelPost, OnlineConsultation,
    ChatbotConversation, ChatbotMessage, CommunicationArchive,
    AccessLog, UserPresence
)

Utilisateur = get_user_model()


# ============================================================================
# SERIALIZERS MESSAGERIE
# ============================================================================

class UtilisateurMinimalSerializer(serializers.ModelSerializer):
    """Serializer minimal pour les références utilisateur"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Utilisateur
        fields = ['id', 'username', 'full_name', 'email']
    
    def get_full_name(self, obj):
        return obj.get_full_name()


class MessageAttachmentSerializer(serializers.ModelSerializer):
    """Serializer pour les pièces jointes"""
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = MessageAttachment
        fields = [
            'id', 'attachment_type', 'file', 'file_url', 'file_name',
            'file_size', 'mime_type', 'thumbnail', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class MessageReadReceiptSerializer(serializers.ModelSerializer):
    """Serializer pour les accusés de lecture"""
    utilisateur_name = serializers.CharField(source='utilisateur.get_full_name', read_only=True)
    
    class Meta:
        model = MessageReadReceipt
        fields = ['id', 'message', 'utilisateur', 'utilisateur_name', 'read_at']
        read_only_fields = ['id', 'read_at']


class MessageSerializer(serializers.ModelSerializer):
    """Serializer pour les messages"""
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    sender = UtilisateurMinimalSerializer(read_only=True)
    attachments = MessageAttachmentSerializer(many=True, read_only=True)
    read_receipts = MessageReadReceiptSerializer(many=True, read_only=True)
    is_read_by_user = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'sender_name', 'message_type',
            'content', 'priority', 'is_encrypted', 'reply_to', 'attachments',
            'read_receipts', 'is_read_by_user', 'is_edited', 'edited_at',
            'is_deleted', 'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'sender', 'created_at', 'updated_at']
    
    def get_is_read_by_user(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.read_receipts.filter(utilisateur=request.user).exists()
        return False


class ConversationParticipantSerializer(serializers.ModelSerializer):
    """Serializer pour les participants"""
    utilisateur = UtilisateurMinimalSerializer(read_only=True)
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ConversationParticipant
        fields = [
            'id', 'conversation', 'utilisateur', 'role', 'is_muted',
            'last_read_at', 'unread_count', 'joined_at'
        ]
        read_only_fields = ['id', 'joined_at']
    
    def get_unread_count(self, obj):
        return obj.get_unread_count()


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer pour les conversations"""
    participants_list = ConversationParticipantSerializer(
        source='conversation_participants',
        many=True,
        read_only=True
    )
    last_message = MessageSerializer(read_only=True)
    unread_count = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'conversation_type', 'name', 'description', 'pharmacie',
            'participants_list', 'last_message', 'unread_count', 'created_by',
            'created_by_name', 'is_active', 'is_archived',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            participant = obj.conversation_participants.filter(
                utilisateur=request.user
            ).first()
            if participant:
                return participant.get_unread_count()
        return 0


# ============================================================================
# SERIALIZERS DOSSIER MÉDICAL
# ============================================================================

class PrescriptionItemSerializer(serializers.ModelSerializer):
    """Serializer pour les lignes d'ordonnance"""
    class Meta:
        model = PrescriptionItem
        fields = [
            'id', 'prescription', 'medication_name', 'dosage', 'form',
            'quantity', 'frequency', 'duration_days', 'instructions',
            'quantity_dispensed', 'is_substitutable', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PrescriptionSerializer(serializers.ModelSerializer):
    """Serializer pour les ordonnances"""
    items = PrescriptionItemSerializer(many=True, read_only=True)
    patient_name = serializers.CharField(source='medical_record.patient.get_full_name', read_only=True)
    validated_by_name = serializers.CharField(source='validated_by.get_full_name', read_only=True)
    is_expired = serializers.SerializerMethodField()
    can_be_renewed = serializers.SerializerMethodField()
    
    class Meta:
        model = Prescription
        fields = [
            'id', 'medical_record', 'patient_name', 'prescription_number',
            'prescriber_name', 'prescriber_license', 'prescription_date',
            'expiry_date', 'status', 'is_renewable', 'renewal_count',
            'max_renewals', 'scan_document', 'notes', 'validated_by',
            'validated_by_name', 'validated_at', 'items', 'is_expired',
            'can_be_renewed', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'prescription_number', 'validated_by', 'validated_at', 'created_at', 'updated_at']
    
    def get_is_expired(self, obj):
        return obj.is_expired()
    
    def get_can_be_renewed(self, obj):
        return obj.can_be_renewed()


class MedicationHistorySerializer(serializers.ModelSerializer):
    """Serializer pour l'historique des médicaments"""
    patient_name = serializers.CharField(source='medical_record.patient.get_full_name', read_only=True)
    dispensed_by_name = serializers.CharField(source='dispensed_by.get_full_name', read_only=True)
    pharmacie_name = serializers.CharField(source='pharmacie.nom', read_only=True)
    
    class Meta:
        model = MedicationHistory
        fields = [
            'id', 'medical_record', 'patient_name', 'prescription',
            'medication_name', 'dosage', 'quantity', 'dispensed_by',
            'dispensed_by_name', 'pharmacie', 'pharmacie_name',
            'dispensed_at', 'price', 'notes'
        ]
        read_only_fields = ['id', 'dispensed_at']


class DrugInteractionAlertSerializer(serializers.ModelSerializer):
    """Serializer pour les alertes d'interaction"""
    patient_name = serializers.CharField(source='medical_record.patient.get_full_name', read_only=True)
    acknowledged_by_name = serializers.CharField(source='acknowledged_by.get_full_name', read_only=True)
    
    class Meta:
        model = DrugInteractionAlert
        fields = [
            'id', 'medical_record', 'patient_name', 'medication_a',
            'medication_b', 'severity', 'description', 'recommendations',
            'is_acknowledged', 'acknowledged_by', 'acknowledged_by_name',
            'acknowledged_at', 'created_at'
        ]
        read_only_fields = ['id', 'acknowledged_by', 'acknowledged_at', 'created_at']


class PatientMedicalRecordSerializer(serializers.ModelSerializer):
    """Serializer pour les dossiers médicaux"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    pharmacie_name = serializers.CharField(source='pharmacie.nom', read_only=True)
    prescriptions = PrescriptionSerializer(many=True, read_only=True)
    medication_history = MedicationHistorySerializer(many=True, read_only=True)
    drug_interaction_alerts = DrugInteractionAlertSerializer(many=True, read_only=True)
    active_alerts_count = serializers.SerializerMethodField()
    
    class Meta:
        model = PatientMedicalRecord
        fields = [
            'id', 'patient', 'patient_name', 'pharmacie', 'pharmacie_name',
            'medical_record_number', 'blood_type', 'allergies',
            'chronic_conditions', 'current_medications', 'emergency_contact',
            'notes', 'is_active', 'prescriptions', 'medication_history',
            'drug_interaction_alerts', 'active_alerts_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'medical_record_number', 'created_at', 'updated_at']
    
    def get_active_alerts_count(self, obj):
        return obj.drug_interaction_alerts.filter(is_acknowledged=False).count()


# ============================================================================
# SERIALIZERS NOTIFICATIONS
# ============================================================================

class NotificationSerializer(serializers.ModelSerializer):
    """Serializer pour les notifications"""
    recipient_name = serializers.CharField(source='recipient.get_full_name', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'recipient_name', 'notification_type',
            'priority', 'title', 'message', 'status', 'is_read',
            'read_at', 'send_in_app', 'send_email', 'send_sms', 'data',
            'related_object_type', 'related_object_id', 'scheduled_for',
            'sent_at', 'created_at'
        ]
        read_only_fields = ['id', 'sent_at', 'created_at']


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer pour les préférences de notification"""
    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'utilisateur', 'enable_in_app', 'enable_email',
            'enable_sms', 'preferences', 'quiet_hours_start',
            'quiet_hours_end', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# SERIALIZERS CANAUX
# ============================================================================

class ChannelPostSerializer(serializers.ModelSerializer):
    """Serializer pour les publications de canaux"""
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    author = UtilisateurMinimalSerializer(read_only=True)
    
    class Meta:
        model = ChannelPost
        fields = [
            'id', 'channel', 'author', 'author_name', 'title', 'content',
            'is_pinned', 'is_announcement', 'attachments', 'tags',
            'is_deleted', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']


class ChannelMembershipSerializer(serializers.ModelSerializer):
    """Serializer pour les adhésions aux canaux"""
    utilisateur = UtilisateurMinimalSerializer(read_only=True)
    
    class Meta:
        model = ChannelMembership
        fields = [
            'id', 'channel', 'utilisateur', 'role', 'is_muted',
            'last_read_at', 'joined_at'
        ]
        read_only_fields = ['id', 'joined_at']


class ChannelSerializer(serializers.ModelSerializer):
    """Serializer pour les canaux"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    pharmacie_name = serializers.CharField(source='pharmacie.nom', read_only=True)
    memberships = ChannelMembershipSerializer(many=True, read_only=True)
    recent_posts = ChannelPostSerializer(many=True, read_only=True, source='posts')
    members_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Channel
        fields = [
            'id', 'pharmacie', 'pharmacie_name', 'name', 'channel_type',
            'description', 'icon', 'color', 'is_private', 'is_archived',
            'created_by', 'created_by_name', 'memberships', 'recent_posts',
            'members_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']
    
    def get_members_count(self, obj):
        return obj.memberships.count()


# ============================================================================
# SERIALIZERS ASSISTANCE EN LIGNE
# ============================================================================

class OnlineConsultationSerializer(serializers.ModelSerializer):
    """Serializer pour les consultations en ligne"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    pharmacie_name = serializers.CharField(source='pharmacie.nom', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    
    class Meta:
        model = OnlineConsultation
        fields = [
            'id', 'patient', 'patient_name', 'pharmacie', 'pharmacie_name',
            'access_code', 'subject', 'question', 'status', 'assigned_to',
            'assigned_to_name', 'response', 'responded_at', 'attachments',
            'is_urgent', 'rating', 'feedback', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'access_code', 'responded_at', 'created_at', 'updated_at']


class ChatbotMessageSerializer(serializers.ModelSerializer):
    """Serializer pour les messages chatbot"""
    class Meta:
        model = ChatbotMessage
        fields = [
            'id', 'conversation', 'sender', 'message', 'intent',
            'confidence', 'suggested_responses', 'metadata', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ChatbotConversationSerializer(serializers.ModelSerializer):
    """Serializer pour les conversations chatbot"""
    utilisateur_name = serializers.CharField(source='utilisateur.get_full_name', read_only=True)
    messages = ChatbotMessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = ChatbotConversation
        fields = [
            'id', 'utilisateur', 'utilisateur_name', 'session_id',
            'pharmacie', 'is_active', 'context', 'messages',
            'created_at', 'last_activity'
        ]
        read_only_fields = ['id', 'session_id', 'created_at', 'last_activity']


# ============================================================================
# SERIALIZERS ARCHIVAGE
# ============================================================================

class CommunicationArchiveSerializer(serializers.ModelSerializer):
    """Serializer pour les archives"""
    pharmacie_name = serializers.CharField(source='pharmacie.nom', read_only=True)
    
    class Meta:
        model = CommunicationArchive
        fields = [
            'id', 'archive_type', 'original_object_id', 'pharmacie',
            'pharmacie_name', 'data', 'participants', 'archived_at'
        ]
        read_only_fields = ['id', 'archived_at']


class AccessLogSerializer(serializers.ModelSerializer):
    """Serializer pour les journaux d'accès"""
    utilisateur_name = serializers.CharField(source='utilisateur.get_full_name', read_only=True)
    
    class Meta:
        model = AccessLog
        fields = [
            'id', 'utilisateur', 'utilisateur_name', 'action',
            'resource_type', 'resource_id', 'ip_address', 'user_agent',
            'details', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']


class UserPresenceSerializer(serializers.ModelSerializer):
    """Serializer pour la présence utilisateur"""
    utilisateur_name = serializers.CharField(source='utilisateur.get_full_name', read_only=True)
    
    class Meta:
        model = UserPresence
        fields = [
            'id', 'utilisateur', 'utilisateur_name', 'status',
            'custom_message', 'last_seen'
        ]
        read_only_fields = ['id', 'last_seen']