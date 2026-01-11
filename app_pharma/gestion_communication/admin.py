"""
Configuration de l'interface d'administration Django
pour la gestion de la communication
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from gestion_communication.models import (
    # Messagerie
    Conversation, ConversationParticipant, Message, MessageAttachment,
    MessageReadReceipt,
    # Dossier médical
    PatientMedicalRecord, Prescription, PrescriptionItem,
    MedicationHistory, DrugInteractionAlert,
    # Notifications
    Notification, NotificationPreference,
    # Canaux
    Channel, ChannelMembership, ChannelPost,
    # Assistance
    OnlineConsultation, ChatbotConversation, ChatbotMessage,
    # Archivage
    CommunicationArchive, AccessLog, UserPresence
)



# Personnalisation du site admin
admin.site.site_header = "Administration Communication Pharmacie"
admin.site.site_title = "Communication Admin"
admin.site.index_title = "Gestion de la communication et messagerie"
# Register your models here.

# ============================================================================
# INLINE ADMIN
# ============================================================================

class ConversationParticipantInline(admin.TabularInline):
    """Inline pour les participants d'une conversation"""
    model = ConversationParticipant
    extra = 0
    fields = ['utilisateur', 'role', 'is_muted', 'last_read_at']
    readonly_fields = ['last_read_at', 'joined_at']


class MessageAttachmentInline(admin.TabularInline):
    """Inline pour les pièces jointes"""
    model = MessageAttachment
    extra = 0
    fields = ['attachment_type', 'file_name', 'file_size', 'created_at']
    readonly_fields = ['created_at']


class PrescriptionItemInline(admin.TabularInline):
    """Inline pour les lignes d'ordonnance"""
    model = PrescriptionItem
    extra = 0
    fields = [
        'medication_name', 'dosage', 'quantity',
        'frequency', 'duration_days', 'quantity_dispensed'
    ]


class ChannelMembershipInline(admin.TabularInline):
    """Inline pour les membres d'un canal"""
    model = ChannelMembership
    extra = 0
    fields = ['utilisateur', 'role', 'is_muted', 'joined_at']
    readonly_fields = ['joined_at']


# ============================================================================
# ADMIN MESSAGERIE
# ============================================================================

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = [
        'name_display', 'conversation_type_badge', 'pharmacie',
        'participants_count', 'last_activity', 'status_badge'
    ]
    list_filter = ['conversation_type', 'is_active', 'is_archived', 'pharmacie', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    inlines = [ConversationParticipantInline]
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('conversation_type', 'name', 'description', 'pharmacie')
        }),
        ('Gestion', {
            'fields': ('created_by', 'is_active', 'is_archived')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def name_display(self, obj):
        if obj.name:
            return obj.name
        participants = obj.participants.all()[:2]
        names = [p.get_full_name() for p in participants]
        return ", ".join(names) if names else "Sans nom"
    name_display.short_description = "Nom"
    
    def conversation_type_badge(self, obj):
        colors = {
            'private': '#6610f2',
            'group': '#20c997',
            'channel': '#fd7e14'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.conversation_type, '#6c757d'),
            obj.get_conversation_type_display()
        )
    conversation_type_badge.short_description = "Type"
    
    def participants_count(self, obj):
        count = obj.participants.count()
        return format_html('<strong>{}</strong> participant(s)', count)
    participants_count.short_description = "Participants"
    
    def last_activity(self, obj):
        return obj.updated_at.strftime('%d/%m/%Y %H:%M')
    last_activity.short_description = "Dernière activité"
    last_activity.admin_order_field = 'updated_at'
    
    def status_badge(self, obj):
        if obj.is_archived:
            return format_html('<span style="color: gray;">📦 Archivée</span>')
        elif obj.is_active:
            return format_html('<span style="color: green;">✓ Active</span>')
        return format_html('<span style="color: red;">✗ Inactive</span>')
    status_badge.short_description = "Statut"
    
    actions = ['archive_conversations', 'activate_conversations']
    
    def archive_conversations(self, request, queryset):
        updated = queryset.update(is_archived=True)
        self.message_user(request, f'{updated} conversation(s) archivée(s).')
    archive_conversations.short_description = "📦 Archiver les conversations"
    
    def activate_conversations(self, request, queryset):
        updated = queryset.update(is_active=True, is_archived=False)
        self.message_user(request, f'{updated} conversation(s) activée(s).')
    activate_conversations.short_description = "✓ Activer les conversations"


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = [
        'sender_name', 'conversation', 'message_type_badge',
        'priority_badge', 'content_preview', 'created_at', 'status_display'
    ]
    list_filter = [
        'message_type', 'priority', 'is_encrypted',
        'is_deleted', 'created_at'
    ]
    search_fields = ['sender__first_name', 'sender__last_name', 'content']
    readonly_fields = ['created_at', 'updated_at', 'edited_at', 'deleted_at']
    date_hierarchy = 'created_at'
    inlines = [MessageAttachmentInline]
    list_per_page = 100
    
    fieldsets = (
        ('Message', {
            'fields': ('conversation', 'sender', 'message_type', 'content', 'priority')
        }),
        ('Sécurité', {
            'fields': ('is_encrypted',)
        }),
        ('Réponse', {
            'fields': ('reply_to',),
            'classes': ('collapse',)
        }),
        ('Édition/Suppression', {
            'fields': ('is_edited', 'edited_at', 'is_deleted', 'deleted_at'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('metadata', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def sender_name(self, obj):
        return obj.sender.get_full_name()
    sender_name.short_description = "Expéditeur"
    
    def message_type_badge(self, obj):
        icons = {
            'text': '💬',
            'image': '🖼️',
            'file': '📎',
            'prescription': '📋',
            'system': '⚙️'
        }
        return format_html(
            '{} {}',
            icons.get(obj.message_type, ''),
            obj.get_message_type_display()
        )
    message_type_badge.short_description = "Type"
    
    def priority_badge(self, obj):
        colors = {
            'low': '#17a2b8',
            'normal': '#28a745',
            'high': '#ffc107',
            'urgent': '#dc3545'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.priority, 'black'),
            obj.get_priority_display()
        )
    priority_badge.short_description = "Priorité"
    
    def content_preview(self, obj):
        if obj.is_deleted:
            return format_html('<em style="color: gray;">Message supprimé</em>')
        preview = obj.content[:50]
        if len(obj.content) > 50:
            preview += '...'
        return preview
    content_preview.short_description = "Aperçu"
    
    def status_display(self, obj):
        badges = []
        if obj.is_encrypted:
            badges.append('🔒')
        if obj.is_edited:
            badges.append('✏️')
        if obj.is_deleted:
            badges.append('🗑️')
        return ' '.join(badges) if badges else '-'
    status_display.short_description = "Statut"


# ============================================================================
# ADMIN DOSSIER MÉDICAL
# ============================================================================

@admin.register(PatientMedicalRecord)
class PatientMedicalRecordAdmin(admin.ModelAdmin):
    list_display = [
        'medical_record_number', 'patient_name', 'pharmacie',
        'blood_type', 'allergies_count', 'is_active'
    ]
    list_filter = ['is_active', 'blood_type', 'pharmacie', 'created_at']
    search_fields = [
        'medical_record_number', 'patient__first_name',
        'patient__last_name', 'notes'
    ]
    readonly_fields = ['medical_record_number', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Patient', {
            'fields': ('patient', 'medical_record_number', 'pharmacie')
        }),
        ('Informations médicales', {
            'fields': ('blood_type', 'allergies', 'chronic_conditions', 'current_medications')
        }),
        ('Contact d\'urgence', {
            'fields': ('emergency_contact',),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Statut', {
            'fields': ('is_active',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def patient_name(self, obj):
        return obj.patient.get_full_name()
    patient_name.short_description = "Patient"
    patient_name.admin_order_field = 'patient__last_name'
    
    def allergies_count(self, obj):
        count = len(obj.allergies) if obj.allergies else 0
        if count > 0:
            return format_html(
                '<span style="color: orange; font-weight: bold;">⚠️ {} allergie(s)</span>',
                count
            )
        return format_html('<span style="color: green;">✓ Aucune</span>')
    allergies_count.short_description = "Allergies"


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = [
        'prescription_number', 'patient_name', 'prescriber_name',
        'prescription_date', 'expiry_status', 'status_badge',
        'renewal_info'
    ]
    list_filter = [
        'status', 'is_renewable', 'prescription_date',
        'expiry_date'
    ]
    search_fields = [
        'prescription_number', 'medical_record__patient__first_name',
        'medical_record__patient__last_name', 'prescriber_name'
    ]
    readonly_fields = ['prescription_number', 'created_at', 'updated_at', 'validated_at']
    date_hierarchy = 'prescription_date'
    inlines = [PrescriptionItemInline]
    
    fieldsets = (
        ('Ordonnance', {
            'fields': (
                'medical_record', 'prescription_number',
                'prescription_date', 'expiry_date'
            )
        }),
        ('Prescripteur', {
            'fields': ('prescriber_name', 'prescriber_license')
        }),
        ('Statut', {
            'fields': ('status', 'is_renewable', 'renewal_count', 'max_renewals')
        }),
        ('Document', {
            'fields': ('scan_document',),
            'classes': ('collapse',)
        }),
        ('Validation', {
            'fields': ('validated_by', 'validated_at'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    def patient_name(self, obj):
        return obj.medical_record.patient.get_full_name()
    patient_name.short_description = "Patient"
    
    def expiry_status(self, obj):
        if obj.is_expired():
            return format_html('<span style="color: red;">❌ Expirée</span>')
        
        days_left = (obj.expiry_date - timezone.now().date()).days
        if days_left <= 7:
            return format_html(
                '<span style="color: orange;">⚠️ {} jour(s)</span>',
                days_left
            )
        return format_html('<span style="color: green;">✓ Valide</span>')
    expiry_status.short_description = "Validité"
    
    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'validated': '#17a2b8',
            'dispensed': '#28a745',
            'partially_dispensed': '#fd7e14',
            'expired': '#dc3545',
            'cancelled': '#6c757d'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = "Statut"
    
    def renewal_info(self, obj):
        if obj.is_renewable:
            return format_html(
                '<span style="color: green;">✓ {}/{}</span>',
                obj.renewal_count, obj.max_renewals
            )
        return format_html('<span style="color: gray;">✗ Non renouvelable</span>')
    renewal_info.short_description = "Renouvellement"
    
    actions = ['validate_prescriptions', 'mark_as_dispensed']
    
    def validate_prescriptions(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='validated',
            validated_by=request.user,
            validated_at=timezone.now()
        )
        self.message_user(request, f'{updated} ordonnance(s) validée(s).')
    validate_prescriptions.short_description = "✓ Valider les ordonnances"
    
    def mark_as_dispensed(self, request, queryset):
        updated = queryset.filter(status='validated').update(status='dispensed')
        self.message_user(request, f'{updated} ordonnance(s) délivrée(s).')
    mark_as_dispensed.short_description = "✓ Marquer comme délivrées"


@admin.register(MedicationHistory)
class MedicationHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'medication_name', 'patient_name', 'quantity',
        'dispensed_by_name', 'pharmacie', 'price_display', 'dispensed_at'
    ]
    list_filter = ['pharmacie', 'dispensed_at']
    search_fields = [
        'medication_name', 'medical_record__patient__first_name',
        'medical_record__patient__last_name'
    ]
    readonly_fields = ['dispensed_at']
    date_hierarchy = 'dispensed_at'
    
    def patient_name(self, obj):
        return obj.medical_record.patient.get_full_name()
    patient_name.short_description = "Patient"
    
    def dispensed_by_name(self, obj):
        return obj.dispensed_by.get_full_name() if obj.dispensed_by else "-"
    dispensed_by_name.short_description = "Délivré par"
    
    def price_display(self, obj):
        return format_html('<strong>{:,.0f} XAF</strong>', obj.price)
    price_display.short_description = "Prix"


@admin.register(DrugInteractionAlert)
class DrugInteractionAlertAdmin(admin.ModelAdmin):
    list_display = [
        'medications_display', 'patient_name', 'severity_badge',
        'is_acknowledged_status', 'created_at'
    ]
    list_filter = ['severity', 'is_acknowledged', 'created_at']
    search_fields = [
        'medication_a', 'medication_b',
        'medical_record__patient__first_name',
        'medical_record__patient__last_name'
    ]
    readonly_fields = ['created_at', 'acknowledged_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Interaction', {
            'fields': ('medical_record', 'medication_a', 'medication_b', 'severity')
        }),
        ('Détails', {
            'fields': ('description', 'recommendations')
        }),
        ('Prise en compte', {
            'fields': ('is_acknowledged', 'acknowledged_by', 'acknowledged_at'),
            'classes': ('collapse',)
        }),
    )
    
    def medications_display(self, obj):
        return format_html(
            '<strong>{}</strong> ⚡ <strong>{}</strong>',
            obj.medication_a, obj.medication_b
        )
    medications_display.short_description = "Médicaments"
    
    def patient_name(self, obj):
        return obj.medical_record.patient.get_full_name()
    patient_name.short_description = "Patient"
    
    def severity_badge(self, obj):
        colors = {
            'minor': '#17a2b8',
            'moderate': '#ffc107',
            'major': '#fd7e14',
            'contraindicated': '#dc3545'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(obj.severity, '#6c757d'),
            obj.get_severity_display()
        )
    severity_badge.short_description = "Sévérité"
    
    def is_acknowledged_status(self, obj):
        if obj.is_acknowledged:
            return format_html(
                '<span style="color: green;">✓ Pris en compte par {}</span>',
                obj.acknowledged_by.get_full_name() if obj.acknowledged_by else 'N/A'
            )
        return format_html('<span style="color: orange;">⏳ En attente</span>')
    is_acknowledged_status.short_description = "Statut"
    
    actions = ['acknowledge_alerts']
    
    def acknowledge_alerts(self, request, queryset):
        updated = queryset.filter(is_acknowledged=False).update(
            is_acknowledged=True,
            acknowledged_by=request.user,
            acknowledged_at=timezone.now()
        )
        self.message_user(request, f'{updated} alerte(s) prise(s) en compte.')
    acknowledge_alerts.short_description = "✓ Prendre en compte"


# ============================================================================
# ADMIN NOTIFICATIONS
# ============================================================================

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'recipient_name', 'notification_type_badge', 'title',
        'priority_badge', 'status_badge', 'channels_display', 'created_at'
    ]
    list_filter = [
        'notification_type', 'priority', 'status', 'is_read',
        'send_in_app', 'send_email', 'send_sms', 'created_at'
    ]
    search_fields = ['recipient__first_name', 'recipient__last_name', 'title', 'message']
    readonly_fields = ['created_at', 'sent_at', 'read_at']
    date_hierarchy = 'created_at'
    list_per_page = 100
    
    fieldsets = (
        ('Destinataire', {
            'fields': ('recipient',)
        }),
        ('Notification', {
            'fields': ('notification_type', 'priority', 'title', 'message')
        }),
        ('Canaux', {
            'fields': ('send_in_app', 'send_email', 'send_sms')
        }),
        ('Statut', {
            'fields': ('status', 'is_read', 'read_at')
        }),
        ('Programmation', {
            'fields': ('scheduled_for', 'sent_at'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('data', 'related_object_type', 'related_object_id'),
            'classes': ('collapse',)
        }),
    )
    
    def recipient_name(self, obj):
        return obj.recipient.get_full_name()
    recipient_name.short_description = "Destinataire"
    
    def notification_type_badge(self, obj):
        icons = {
            'prescription_pending': '📋',
            'prescription_ready': '✅',
            'prescription_expiring': '⏰',
            'stock_low': '📦',
            'stock_out': '❌',
            'medication_reminder': '💊',
            'leave_request': '🏖️',
            'message': '💬',
            'drug_interaction': '⚠️',
            'appointment': '📅',
            'system': '⚙️'
        }
        return format_html(
            '{} {}',
            icons.get(obj.notification_type, ''),
            obj.get_notification_type_display()
        )
    notification_type_badge.short_description = "Type"
    
    def priority_badge(self, obj):
        colors = {
            'low': '#17a2b8',
            'normal': '#28a745',
            'high': '#ffc107',
            'urgent': '#dc3545'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.priority, 'black'),
            obj.get_priority_display()
        )
    priority_badge.short_description = "Priorité"
    
    def status_badge(self, obj):
        colors = {
            'pending': '#6c757d',
            'sent': '#17a2b8',
            'delivered': '#28a745',
            'read': '#20c997',
            'failed': '#dc3545'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    status_badge.short_description = "Statut"
    
    def channels_display(self, obj):
        channels = []
        if obj.send_in_app:
            channels.append('📱 App')
        if obj.send_email:
            channels.append('✉️ Email')
        if obj.send_sms:
            channels.append('📲 SMS')
        return ' | '.join(channels) if channels else '-'
    channels_display.short_description = "Canaux"
    
    actions = ['mark_as_sent', 'mark_as_read']
    
    def mark_as_sent(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='sent',
            sent_at=timezone.now()
        )
        self.message_user(request, f'{updated} notification(s) marquée(s) comme envoyée(s).')
    mark_as_sent.short_description = "📤 Marquer comme envoyées"
    
    def mark_as_read(self, request, queryset):
        updated = queryset.update(
            is_read=True,
            read_at=timezone.now()
        )
        self.message_user(request, f'{updated} notification(s) marquée(s) comme lue(s).')
    mark_as_read.short_description = "✓ Marquer comme lues"


# ============================================================================
# ADMIN CANAUX
# ============================================================================

@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = [
        'name_with_icon', 'channel_type_badge', 'pharmacie',
        'members_count', 'privacy_badge', 'is_archived'
    ]
    list_filter = ['channel_type', 'is_private', 'is_archived', 'pharmacie', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    inlines = [ChannelMembershipInline]
    
    fieldsets = (
        ('Canal', {
            'fields': ('pharmacie', 'name', 'channel_type', 'description')
        }),
        ('Apparence', {
            'fields': ('icon', 'color')
        }),
        ('Paramètres', {
            'fields': ('is_private', 'is_archived', 'created_by')
        }),
    )
    
    def name_with_icon(self, obj):
        icon = obj.icon if obj.icon else '#'
        return format_html(
            '<span style="font-size: 16px;">{}</span> <strong>{}</strong>',
            icon, obj.name
        )
    name_with_icon.short_description = "Nom"
    
    def channel_type_badge(self, obj):
        colors = {
            'urgent': '#dc3545',
            'stock': '#ffc107',
            'security': '#fd7e14',
            'news': '#17a2b8',
            'general': '#28a745',
            'custom': '#6610f2'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.channel_type, '#6c757d'),
            obj.get_channel_type_display()
        )
    channel_type_badge.short_description = "Type"
    
    def members_count(self, obj):
        count = obj.members.count()
        return format_html('<strong>{}</strong> membre(s)', count)
    members_count.short_description = "Membres"
    
    def privacy_badge(self, obj):
        if obj.is_private:
            return format_html('<span style="color: orange;">🔒 Privé</span>')
        return format_html('<span style="color: green;">🌍 Public</span>')
    privacy_badge.short_description = "Visibilité"


@admin.register(ChannelPost)
class ChannelPostAdmin(admin.ModelAdmin):
    list_display = [
        'channel', 'author_name', 'title_or_preview',
        'post_type_badge', 'created_at'
    ]
    list_filter = ['is_pinned', 'is_announcement', 'is_deleted', 'created_at']
    search_fields = ['title', 'content', 'author__first_name', 'author__last_name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    def author_name(self, obj):
        return obj.author.get_full_name()
    author_name.short_description = "Auteur"
    
    def title_or_preview(self, obj):
        if obj.title:
            return obj.title
        preview = obj.content[:50]
        if len(obj.content) > 50:
            preview += '...'
        return preview
    title_or_preview.short_description = "Titre/Aperçu"
    
    def post_type_badge(self, obj):
        badges = []
        if obj.is_pinned:
            badges.append('📌 Épinglé')
        if obj.is_announcement:
            badges.append('📢 Annonce')
        if obj.is_deleted:
            badges.append('🗑️ Supprimé')
        return ' | '.join(badges) if badges else 'Standard'
    post_type_badge.short_description = "Type"
    
    actions = ['pin_posts', 'unpin_posts']
    
    def pin_posts(self, request, queryset):
        updated = queryset.update(is_pinned=True)
        self.message_user(request, f'{updated} publication(s) épinglée(s).')
    pin_posts.short_description = "📌 Épingler"
    
    def unpin_posts(self, request, queryset):
        updated = queryset.update(is_pinned=False)
        self.message_user(request, f'{updated} publication(s) désépinglée(s).')
    unpin_posts.short_description = "📌 Désépingler"


# ============================================================================
# ADMIN ASSISTANCE
# ============================================================================

@admin.register(OnlineConsultation)
class OnlineConsultationAdmin(admin.ModelAdmin):
    list_display = [
        'access_code', 'patient_name', 'subject',
        'status_badge', 'urgency_badge', 'assigned_to_name',
        'rating_display', 'created_at'
    ]
    list_filter = ['status', 'is_urgent', 'pharmacie', 'created_at']
    search_fields = [
        'access_code', 'patient__first_name',
        'patient__last_name', 'subject', 'question'
    ]
    readonly_fields = ['access_code', 'created_at', 'updated_at', 'responded_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Consultation', {
            'fields': ('patient', 'pharmacie', 'access_code', 'subject', 'is_urgent')
        }),
        ('Question', {
            'fields': ('question', 'attachments')
        }),
        ('Traitement', {
            'fields': ('status', 'assigned_to', 'response', 'responded_at')
        }),
        ('Évaluation', {
            'fields': ('rating', 'feedback'),
            'classes': ('collapse',)
        }),
    )
    
    def patient_name(self, obj):
        return obj.patient.get_full_name()
    patient_name.short_description = "Patient"
    
    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'in_progress': '#17a2b8',
            'answered': '#28a745',
            'closed': '#6c757d',
            'cancelled': '#dc3545'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = "Statut"
    
    def urgency_badge(self, obj):
        if obj.is_urgent:
            return format_html('<span style="color: red; font-weight: bold;">🚨 URGENT</span>')
        return format_html('<span style="color: green;">Normal</span>')
    urgency_badge.short_description = "Urgence"
    
    def assigned_to_name(self, obj):
        return obj.assigned_to.get_full_name() if obj.assigned_to else "-"
    assigned_to_name.short_description = "Assigné à"
    
    def rating_display(self, obj):
        if obj.rating:
            stars = '⭐' * obj.rating
            return format_html('<span style="font-size: 14px;">{}</span>', stars)
        return '-'
    rating_display.short_description = "Note"
    
    actions = ['assign_to_me', 'mark_as_answered']
    
    def assign_to_me(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            assigned_to=request.user,
            status='in_progress'
        )
        self.message_user(request, f'{updated} consultation(s) assignée(s) à vous.')
    assign_to_me.short_description = "👤 M'assigner"
    
    def mark_as_answered(self, request, queryset):
        updated = queryset.filter(status='in_progress').update(
            status='answered',
            responded_at=timezone.now()
        )
        self.message_user(request, f'{updated} consultation(s) marquée(s) comme répondue(s).')
    mark_as_answered.short_description = "✓ Marquer comme répondue"


@admin.register(ChatbotConversation)
class ChatbotConversationAdmin(admin.ModelAdmin):
    list_display = [
        'session_id', 'user_display', 'pharmacie',
        'messages_count', 'is_active', 'last_activity'
    ]
    list_filter = ['is_active', 'pharmacie', 'created_at']
    search_fields = ['session_id', 'utilisateur__first_name', 'utilisateur__last_name']
    readonly_fields = ['session_id', 'created_at', 'last_activity']
    date_hierarchy = 'last_activity'
    
    def user_display(self, obj):
        if obj.utilisateur:
            return obj.utilisateur.get_full_name()
        return format_html('<em style="color: gray;">Anonyme</em>')
    user_display.short_description = "Utilisateur"
    
    def messages_count(self, obj):
        count = obj.messages.count()
        return format_html('<strong>{}</strong> message(s)', count)
    messages_count.short_description = "Messages"


# ============================================================================
# ADMIN ARCHIVAGE
# ============================================================================

@admin.register(CommunicationArchive)
class CommunicationArchiveAdmin(admin.ModelAdmin):
    list_display = [
        'archive_type_badge', 'original_object_id',
        'pharmacie', 'participants_count', 'archived_at'
    ]
    list_filter = ['archive_type', 'pharmacie', 'archived_at']
    search_fields = ['original_object_id']
    readonly_fields = ['archived_at']
    date_hierarchy = 'archived_at'
    
    def archive_type_badge(self, obj):
        icons = {
            'message': '💬',
            'consultation': '👨‍⚕️',
            'prescription': '📋',
            'channel_post': '📢'
        }
        return format_html(
            '{} {}',
            icons.get(obj.archive_type, ''),
            obj.get_archive_type_display()
        )
    archive_type_badge.short_description = "Type"
    
    def participants_count(self, obj):
        count = len(obj.participants) if obj.participants else 0
        return f"{count} participant(s)"
    participants_count.short_description = "Participants"


@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = [
        'utilisateur_name', 'action_badge', 'resource_type',
        'ip_address', 'timestamp'
    ]
    list_filter = ['action', 'resource_type', 'timestamp']
    search_fields = [
        'utilisateur__first_name', 'utilisateur__last_name',
        'resource_type', 'ip_address'
    ]
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    list_per_page = 100
    
    def utilisateur_name(self, obj):
        return obj.utilisateur.get_full_name()
    utilisateur_name.short_description = "Utilisateur"
    
    def action_badge(self, obj):
        icons = {
            'view': '👁️',
            'create': '➕',
            'update': '✏️',
            'delete': '🗑️',
            'export': '📥',
            'share': '🔗'
        }
        colors = {
            'view': '#17a2b8',
            'create': '#28a745',
            'update': '#ffc107',
            'delete': '#dc3545',
            'export': '#6610f2',
            'share': '#fd7e14'
        }
        return format_html(
            '<span style="color: {};">{} {}</span>',
            colors.get(obj.action, 'black'),
            icons.get(obj.action, ''),
            obj.get_action_display()
        )
    action_badge.short_description = "Action"


@admin.register(UserPresence)
class UserPresenceAdmin(admin.ModelAdmin):
    list_display = [
        'utilisateur_name', 'status_badge', 'custom_message',
        'last_seen_display'
    ]
    list_filter = ['status', 'last_seen']
    search_fields = ['utilisateur__first_name', 'utilisateur__last_name']
    readonly_fields = ['last_seen']
    
    def utilisateur_name(self, obj):
        return obj.utilisateur.get_full_name()
    utilisateur_name.short_description = "Utilisateur"
    
    def status_badge(self, obj):
        icons = {
            'online': '🟢',
            'away': '🟡',
            'busy': '🔴',
            'offline': '⚫'
        }
        colors = {
            'online': '#28a745',
            'away': '#ffc107',
            'busy': '#dc3545',
            'offline': '#6c757d'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            colors.get(obj.status, 'black'),
            icons.get(obj.status, ''),
            obj.get_status_display()
        )
    status_badge.short_description = "Statut"
    
    def last_seen_display(self, obj):
        now = timezone.now()
        diff = now - obj.last_seen
        
        if diff.seconds < 60:
            return "À l'instant"
        elif diff.seconds < 3600:
            minutes = diff.seconds // 60
            return f"Il y a {minutes} min"
        elif diff.days == 0:
            hours = diff.seconds // 3600
            return f"Il y a {hours}h"
        elif diff.days == 1:
            return "Hier"
        else:
            return f"Il y a {diff.days} jour(s)"
    last_seen_display.short_description = "Dernière activité"



