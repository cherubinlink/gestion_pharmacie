"""
Admin pour le Suivi Médical & CRM Marketing
Interface d'administration complète avec badges, filtres et actions
Applications 7 & 8
"""
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Sum
from django.urls import reverse
from django.utils import timezone

# Import des modèles
from .models import (
    # Médecins et profils
    Doctor, MedicalProfile, DoctorPatientLink,
    # Pathologies et allergies
    MedicalCondition, PatientCondition, Allergen, PatientAllergy,
    # Ordonnances et traitements
    Prescription, PrescriptionItem, Treatment, TreatmentMedication,
    # DME et interactions
    ExternalMedicalRecord, Appointment, PatientMessage,
    # Programme fidélité
    LoyaltyProgram, LoyaltyTier, CustomerLoyalty, LoyaltyTransaction,
    # Marketing et CRM
    MarketingCampaign, CampaignRecipient, CustomerSegment, Lead,
    AutomatedReminder
)

# Register your models here.


# ============================================================================
# ADMIN MÉDECINS ET PROFILS MÉDICAUX
# ============================================================================

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    """Admin pour les médecins"""
    list_display = [
        'doctor_code', 'get_full_name_display', 'speciality_badge',
        'phone', 'license_number', 'hospital',
        'total_patients_display', 'is_active_badge',
        'created_at'
    ]
    list_filter = ['speciality', 'is_active', 'pharmacie', 'created_at']
    search_fields = ['doctor_code', 'first_name', 'last_name', 'license_number', 'email', 'phone']
    readonly_fields = ['doctor_code', 'created_at', 'updated_at']
    autocomplete_fields = ['pharmacie']
    
    fieldsets = (
        ('Identification', {
            'fields': ('pharmacie', 'doctor_code', 'title', 'first_name', 'last_name')
        }),
        ('Spécialité', {
            'fields': ('speciality', 'license_number', 'hospital')
        }),
        ('Contact', {
            'fields': ('phone', 'mobile', 'email', 'address', 'city')
        }),
        ('Statut', {
            'fields': ('is_active', 'notes')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_full_name_display(self, obj):
        return obj.get_full_name()
    get_full_name_display.short_description = 'Médecin'
    
    def speciality_badge(self, obj):
        colors = {
            'general_practitioner': '#28a745',
            'cardiologist': '#dc3545',
            'dermatologist': '#ffc107',
            'endocrinologist': '#17a2b8',
            'gynecologist': '#e83e8c',
            'pediatrician': '#fd7e14',
        }
        color = colors.get(obj.speciality, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_speciality_display()
        )
    speciality_badge.short_description = 'Spécialité'
    
    def total_patients_display(self, obj):
        count = obj.patient_links.filter(is_active=True).count()
        return format_html('<strong style="color: #007bff;">{} patients</strong>', count)
    total_patients_display.short_description = 'Patients'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green; font-size: 16px;">✓ Actif</span>')
        return format_html('<span style="color: red; font-size: 16px;">✗ Inactif</span>')
    is_active_badge.short_description = 'Statut'


@admin.register(MedicalProfile)
class MedicalProfileAdmin(admin.ModelAdmin):
    """Admin pour les profils médicaux"""
    list_display = [
        'patient', 'blood_type_badge', 'bmi_display', 
        'primary_doctor', 'consent_status',
        'last_checkup_date', 'updated_at'
    ]
    list_filter = ['blood_type', 'consent_data_usage', 'consent_communication']
    search_fields = ['patient__first_name', 'patient__last_name', 'insurance_provider']
    autocomplete_fields = ['patient', 'primary_doctor']
    readonly_fields = ['created_at', 'updated_at', 'bmi_calculated']
    
    fieldsets = (
        ('Patient', {
            'fields': ('patient',)
        }),
        ('Informations médicales', {
            'fields': ('blood_type', 'height', 'weight', 'bmi_calculated')
        }),
        ('Médecin traitant', {
            'fields': ('primary_doctor',)
        }),
        ('Contact d\'urgence', {
            'fields': ('emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relation')
        }),
        ('Assurance', {
            'fields': ('insurance_provider', 'insurance_number')
        }),
        ('Consentements RGPD', {
            'fields': ('consent_data_usage', 'consent_communication')
        }),
        ('Notes', {
            'fields': ('medical_notes', 'last_checkup_date')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def blood_type_badge(self, obj):
        colors = {
            'A+': '#dc3545', 'A-': '#dc3545',
            'B+': '#28a745', 'B-': '#28a745',
            'AB+': '#ffc107', 'AB-': '#ffc107',
            'O+': '#17a2b8', 'O-': '#17a2b8',
        }
        color = colors.get(obj.blood_type, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.get_blood_type_display()
        )
    blood_type_badge.short_description = 'Groupe sanguin'
    
    def bmi_display(self, obj):
        bmi = obj.calculate_bmi()
        if bmi:
            if bmi < 18.5:
                color = '#ffc107'
                status = 'Sous-poids'
            elif bmi < 25:
                color = '#28a745'
                status = 'Normal'
            elif bmi < 30:
                color = '#fd7e14'
                status = 'Surpoids'
            else:
                color = '#dc3545'
                status = 'Obésité'
            return format_html(
                '<strong style="color: {};">{:.1f}</strong> <small>({})</small>',
                color, bmi, status
            )
        return '-'
    bmi_display.short_description = 'IMC'
    
    def bmi_calculated(self, obj):
        bmi = obj.calculate_bmi()
        return f"{bmi:.2f}" if bmi else "Non calculable"
    bmi_calculated.short_description = 'IMC calculé'
    
    def consent_status(self, obj):
        if obj.consent_data_usage and obj.consent_communication:
            return format_html('<span style="color: green;">✓ Complet</span>')
        elif obj.consent_data_usage or obj.consent_communication:
            return format_html('<span style="color: orange;">◐ Partiel</span>')
        return format_html('<span style="color: red;">✗ Aucun</span>')
    consent_status.short_description = 'Consentements'


@admin.register(DoctorPatientLink)
class DoctorPatientLinkAdmin(admin.ModelAdmin):
    """Admin pour les liens médecin-patient"""
    list_display = [
        'patient', 'doctor', 'is_primary_badge',
        'relation_type_badge', 'start_date',
        'is_active_badge', 'created_at'
    ]
    list_filter = ['is_primary', 'relation_type', 'is_active', 'start_date']
    search_fields = ['patient__first_name', 'patient__last_name', 'doctor__first_name', 'doctor__last_name']
    autocomplete_fields = ['patient', 'doctor']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Patient et Médecin', {
            'fields': ('patient', 'doctor')
        }),
        ('Relation', {
            'fields': ('is_primary', 'relation_type')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date')
        }),
        ('Statut et Notes', {
            'fields': ('is_active', 'notes')
        }),
        ('Métadonnées', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    
    def is_primary_badge(self, obj):
        if obj.is_primary:
            return format_html('<span style="background: #28a745; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">⭐ Médecin traitant</span>')
        return format_html('<span style="color: #6c757d;">Autre médecin</span>')
    is_primary_badge.short_description = 'Type'
    
    def relation_type_badge(self, obj):
        colors = {
            'regular': '#007bff',
            'consultation': '#ffc107',
            'specialist': '#17a2b8',
        }
        color = colors.get(obj.relation_type, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_relation_type_display()
        )
    relation_type_badge.short_description = 'Relation'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Actif</span>')
        return format_html('<span style="color: red;">✗ Inactif</span>')
    is_active_badge.short_description = 'Statut'


# ============================================================================
# ADMIN PATHOLOGIES ET ALLERGIES
# ============================================================================

@admin.register(MedicalCondition)
class MedicalConditionAdmin(admin.ModelAdmin):
    """Admin pour les pathologies"""
    list_display = [
        'code', 'name', 'condition_type_badge',
        'category', 'total_cases', 'is_active_badge',
        'created_at'
    ]
    list_filter = ['condition_type', 'is_active', 'category']
    search_fields = ['code', 'name', 'description', 'category']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Identification', {
            'fields': ('code', 'name', 'condition_type')
        }),
        ('Description', {
            'fields': ('description', 'symptoms', 'category')
        }),
        ('Statut', {
            'fields': ('is_active',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def condition_type_badge(self, obj):
        colors = {
            'chronic': '#dc3545',
            'acute': '#ffc107',
            'genetic': '#e83e8c',
            'infectious': '#fd7e14',
            'autoimmune': '#17a2b8',
            'mental': '#6f42c1',
        }
        color = colors.get(obj.condition_type, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_condition_type_display()
        )
    condition_type_badge.short_description = 'Type'
    
    def total_cases(self, obj):
        count = obj.patient_cases.filter(status='active').count()
        return format_html('<strong style="color: #dc3545;">{} cas actif(s)</strong>', count)
    total_cases.short_description = 'Cas actifs'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Active</span>')
        return format_html('<span style="color: red;">✗ Inactive</span>')
    is_active_badge.short_description = 'Statut'


@admin.register(PatientCondition)
class PatientConditionAdmin(admin.ModelAdmin):
    """Admin pour les pathologies patient"""
    list_display = [
        'patient', 'condition', 'diagnosis_date',
        'severity_badge', 'status_badge',
        'diagnosed_by', 'updated_at'
    ]
    list_filter = ['severity', 'status', 'diagnosis_date', 'condition__condition_type']
    search_fields = ['patient__first_name', 'patient__last_name', 'condition__name', 'condition__code']
    autocomplete_fields = ['patient', 'condition', 'diagnosed_by']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Patient et Pathologie', {
            'fields': ('patient', 'condition')
        }),
        ('Dates', {
            'fields': ('diagnosis_date', 'resolved_date')
        }),
        ('Sévérité et Statut', {
            'fields': ('severity', 'status')
        }),
        ('Diagnostic', {
            'fields': ('diagnosed_by',)
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def severity_badge(self, obj):
        colors = {
            'mild': '#28a745',
            'moderate': '#ffc107',
            'severe': '#fd7e14',
            'critical': '#dc3545'
        }
        color = colors.get(obj.severity, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_severity_display()
        )
    severity_badge.short_description = 'Sévérité'
    
    def status_badge(self, obj):
        colors = {
            'active': '#dc3545',
            'in_remission': '#ffc107',
            'resolved': '#28a745',
            'chronic': '#6c757d'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Statut'


@admin.register(Allergen)
class AllergenAdmin(admin.ModelAdmin):
    """Admin pour les allergènes"""
    list_display = [
        'name', 'allergen_type_badge',
        'active_substance', 'total_cases',
        'is_active_badge', 'created_at'
    ]
    list_filter = ['allergen_type', 'is_active']
    search_fields = ['name', 'active_substance', 'description']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Identification', {
            'fields': ('name', 'allergen_type')
        }),
        ('Détails', {
            'fields': ('active_substance', 'description', 'common_reactions')
        }),
        ('Statut', {
            'fields': ('is_active',)
        }),
        ('Métadonnées', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    
    def allergen_type_badge(self, obj):
        colors = {
            'medication': '#dc3545',
            'food': '#28a745',
            'environment': '#17a2b8',
            'animal': '#ffc107',
            'insect': '#fd7e14',
            'chemical': '#6f42c1',
        }
        icons = {
            'medication': '💊',
            'food': '🍽️',
            'environment': '🌿',
            'animal': '🐾',
            'insect': '🐛',
            'chemical': '🧪',
        }
        color = colors.get(obj.allergen_type, '#6c757d')
        icon = icons.get(obj.allergen_type, '●')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px;">{} {}</span>',
            color, icon, obj.get_allergen_type_display()
        )
    allergen_type_badge.short_description = 'Type'
    
    def total_cases(self, obj):
        count = obj.patient_cases.filter(is_active=True).count()
        return format_html('<strong style="color: #dc3545;">{} patient(s)</strong>', count)
    total_cases.short_description = 'Patients affectés'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Actif</span>')
        return format_html('<span style="color: red;">✗ Inactif</span>')
    is_active_badge.short_description = 'Statut'


@admin.register(PatientAllergy)
class PatientAllergyAdmin(admin.ModelAdmin):
    """Admin pour les allergies patient"""
    list_display = [
        'patient', 'allergen', 'severity_badge',
        'reaction_type', 'diagnosed_by',
        'is_active_badge', 'created_at'
    ]
    list_filter = ['severity', 'reaction_type', 'is_active', 'allergen__allergen_type']
    search_fields = ['patient__first_name', 'patient__last_name', 'allergen__name']
    autocomplete_fields = ['patient', 'allergen', 'diagnosed_by']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Patient et allergène', {
            'fields': ('patient', 'allergen')
        }),
        ('Détails allergie', {
            'fields': ('severity', 'reaction_type', 'symptoms')
        }),
        ('Dates', {
            'fields': ('first_occurrence_date', 'last_occurrence_date')
        }),
        ('Diagnostic', {
            'fields': ('diagnosed_by',)
        }),
        ('Urgence', {
            'fields': ('emergency_instructions',),
            'classes': ('collapse',)
        }),
        ('Statut et notes', {
            'fields': ('is_active', 'notes')
        })
    )
    
    def severity_badge(self, obj):
        colors = {
            'mild': '#28a745',
            'moderate': '#ffc107',
            'severe': '#fd7e14',
            'life_threatening': '#dc3545'
        }
        icons = {
            'mild': '●',
            'moderate': '◉',
            'severe': '◉◉',
            'life_threatening': '🚨'
        }
        color = colors.get(obj.severity, '#6c757d')
        icon = icons.get(obj.severity, '●')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_severity_display()
        )
    severity_badge.short_description = 'Sévérité'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: #dc3545; font-weight: bold;">⚠️ Active</span>')
        return format_html('<span style="color: #6c757d;">Inactive</span>')
    is_active_badge.short_description = 'Statut'
    
    actions = ['mark_inactive', 'mark_active']
    
    def mark_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} allergie(s) marquée(s) comme inactive(s).')
    mark_inactive.short_description = 'Marquer comme inactive'
    
    def mark_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} allergie(s) marquée(s) comme active(s).')
    mark_active.short_description = 'Marquer comme active'


# ============================================================================
# ADMIN ORDONNANCES ET TRAITEMENTS
# ============================================================================

class PrescriptionItemInline(admin.TabularInline):
    """Inline pour les lignes d'ordonnance"""
    model = PrescriptionItem
    extra = 1
    autocomplete_fields = ['product']
    fields = ['product', 'quantity', 'dosage', 'frequency', 'duration', 'substitution_allowed', 'quantity_dispensed']


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    """Admin pour les ordonnances"""
    list_display = [
        'prescription_number', 'patient', 'doctor',
        'prescription_date', 'status_badge',
        'is_renewable_badge', 'items_count',
        'created_at'
    ]
    list_filter = ['status', 'is_renewable', 'prescription_date']
    search_fields = ['prescription_number', 'patient__first_name', 'patient__last_name', 'doctor__last_name']
    autocomplete_fields = ['patient', 'doctor', 'dispensed_by']
    readonly_fields = ['prescription_number', 'created_at', 'updated_at']
    inlines = [PrescriptionItemInline]
    
    fieldsets = (
        ('Identification', {
            'fields': ('prescription_number', 'patient', 'doctor')
        }),
        ('Dates', {
            'fields': ('prescription_date', 'expiry_date')
        }),
        ('Diagnostic', {
            'fields': ('diagnosis',)
        }),
        ('Statut', {
            'fields': ('status',)
        }),
        ('Renouvellement', {
            'fields': ('is_renewable', 'renewal_count', 'renewals_remaining')
        }),
        ('Document', {
            'fields': ('prescription_file',)
        }),
        ('Notes', {
            'fields': ('notes', 'pharmacist_notes')
        }),
        ('Délivrance', {
            'fields': ('dispensed_at', 'dispensed_by'),
            'classes': ('collapse',)
        })
    )
    
    def status_badge(self, obj):
        colors = {
            'active': '#28a745',
            'completed': '#17a2b8',
            'cancelled': '#dc3545',
            'expired': '#6c757d'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Statut'
    
    def is_renewable_badge(self, obj):
        if obj.is_renewable:
            return format_html(
                '<span style="color: green;">✓ Renouvelable ({}/{})</span>',
                obj.renewal_count - obj.renewals_remaining, obj.renewal_count
            )
        return format_html('<span style="color: #6c757d;">Non renouvelable</span>')
    is_renewable_badge.short_description = 'Renouvellement'
    
    def items_count(self, obj):
        count = obj.items.count()
        return format_html('<strong>{} médicament(s)</strong>', count)
    items_count.short_description = 'Lignes'
    
    actions = ['mark_as_dispensed', 'mark_as_expired']
    
    def mark_as_dispensed(self, request, queryset):
        updated = queryset.update(status='completed', dispensed_at=timezone.now(), dispensed_by=request.user)
        self.message_user(request, f'{updated} ordonnance(s) marquée(s) comme délivrée(s).')
    mark_as_dispensed.short_description = 'Marquer comme délivrée'
    
    def mark_as_expired(self, request, queryset):
        updated = queryset.update(status='expired')
        self.message_user(request, f'{updated} ordonnance(s) expirée(s).')
    mark_as_expired.short_description = 'Marquer comme expirée'


class TreatmentMedicationInline(admin.TabularInline):
    """Inline pour les médicaments du traitement"""
    model = TreatmentMedication
    extra = 1
    autocomplete_fields = ['product']
    fields = ['product', 'dosage', 'frequency', 'start_date', 'end_date', 'is_active']


@admin.register(Treatment)
class TreatmentAdmin(admin.ModelAdmin):
    """Admin pour les traitements"""
    list_display = [
        'name', 'patient', 'status_badge',
        'start_date', 'end_date',
        'reminder_badge', 'medications_count',
        'created_at'
    ]
    list_filter = ['status', 'reminder_enabled', 'start_date']
    search_fields = ['name', 'patient__first_name', 'patient__last_name']
    autocomplete_fields = ['patient', 'condition', 'prescription', 'doctor']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [TreatmentMedicationInline]
    
    fieldsets = (
        ('Patient', {
            'fields': ('patient',)
        }),
        ('Traitement', {
            'fields': ('name', 'description', 'condition', 'prescription')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date', 'actual_end_date')
        }),
        ('Statut', {
            'fields': ('status',)
        }),
        ('Suivi médical', {
            'fields': ('doctor',)
        }),
        ('Rappels automatiques', {
            'fields': ('reminder_enabled', 'reminder_frequency')
        }),
        ('Notes', {
            'fields': ('notes',)
        })
    )
    
    def status_badge(self, obj):
        colors = {
            'active': '#28a745',
            'completed': '#17a2b8',
            'paused': '#ffc107',
            'discontinued': '#dc3545'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Statut'
    
    def reminder_badge(self, obj):
        if obj.reminder_enabled:
            return format_html('<span style="color: green;">🔔 {} </span>', obj.reminder_frequency or 'Activé')
        return format_html('<span style="color: #6c757d;">🔕 Désactivé</span>')
    reminder_badge.short_description = 'Rappels'
    
    def medications_count(self, obj):
        count = obj.medications.filter(is_active=True).count()
        return format_html('<strong>{} médicament(s)</strong>', count)
    medications_count.short_description = 'Médicaments'


# ============================================================================
# ADMIN DOSSIERS MÉDICAUX EXTERNES ET RENDEZ-VOUS
# ============================================================================

@admin.register(ExternalMedicalRecord)
class ExternalMedicalRecordAdmin(admin.ModelAdmin):
    """Admin pour les dossiers médicaux externes"""
    list_display = [
        'record_date', 'patient', 'title',
        'record_type_badge', 'source_system_badge',
        'is_verified_badge', 'import_date'
    ]
    list_filter = ['record_type', 'source_system', 'is_verified', 'record_date']
    search_fields = ['patient__first_name', 'patient__last_name', 'title', 'external_id', 'source_name']
    autocomplete_fields = ['patient', 'doctor', 'verified_by']
    readonly_fields = ['import_date', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Patient', {
            'fields': ('patient',)
        }),
        ('Identification', {
            'fields': ('external_id', 'record_type', 'title')
        }),
        ('Source', {
            'fields': ('source_system', 'source_name')
        }),
        ('Contenu', {
            'fields': ('content', 'doctor', 'document_file')
        }),
        ('Dates', {
            'fields': ('record_date', 'import_date')
        }),
        ('Interopérabilité FHIR', {
            'fields': ('fhir_resource_type', 'fhir_resource_id'),
            'classes': ('collapse',)
        }),
        ('Vérification', {
            'fields': ('is_verified', 'verified_by', 'verified_at')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def record_type_badge(self, obj):
        colors = {
            'consultation': '#007bff',
            'lab_result': '#28a745',
            'imaging': '#17a2b8',
            'surgery': '#dc3545',
            'hospitalization': '#ffc107',
            'vaccination': '#e83e8c',
        }
        icons = {
            'consultation': '🩺',
            'lab_result': '🔬',
            'imaging': '📷',
            'surgery': '⚕️',
            'hospitalization': '🏥',
            'vaccination': '💉',
        }
        color = colors.get(obj.record_type, '#6c757d')
        icon = icons.get(obj.record_type, '📋')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px;">{} {}</span>',
            color, icon, obj.get_record_type_display()
        )
    record_type_badge.short_description = 'Type'
    
    def source_system_badge(self, obj):
        colors = {
            'hospital': '#dc3545',
            'clinic': '#28a745',
            'laboratory': '#17a2b8',
            'imaging_center': '#ffc107',
            'specialist': '#6f42c1',
        }
        color = colors.get(obj.source_system, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_source_system_display()
        )
    source_system_badge.short_description = 'Source'
    
    def is_verified_badge(self, obj):
        if obj.is_verified:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Vérifié</span><br/>'
                '<small>par {} le {}</small>',
                obj.verified_by.get_full_name() if obj.verified_by else 'N/A',
                obj.verified_at.strftime('%d/%m/%Y') if obj.verified_at else ''
            )
        return format_html('<span style="color: orange;">⚠️ Non vérifié</span>')
    is_verified_badge.short_description = 'Vérification'
    
    actions = ['mark_as_verified']
    
    def mark_as_verified(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(
            is_verified=True,
            verified_by=request.user,
            verified_at=timezone.now()
        )
        self.message_user(request, f'{updated} dossier(s) marqué(s) comme vérifié(s).')
    mark_as_verified.short_description = 'Marquer comme vérifié'


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    """Admin pour les rendez-vous"""
    list_display = [
        'appointment_datetime', 'patient', 'appointment_type_badge',
        'pharmacist', 'status_badge', 'duration_minutes',
        'reminder_status', 'created_at'
    ]
    list_filter = ['appointment_type', 'status', 'pharmacie', 'appointment_datetime']
    search_fields = ['patient__first_name', 'patient__last_name', 'reason']
    autocomplete_fields = ['pharmacie', 'patient', 'pharmacist', 'created_by']
    readonly_fields = ['created_at', 'updated_at']
    
    def appointment_type_badge(self, obj):
        colors = {
            'consultation': '#007bff',
            'medication_review': '#28a745',
            'vaccination': '#ffc107',
            'blood_pressure': '#dc3545',
            'blood_sugar': '#fd7e14',
        }
        color = colors.get(obj.appointment_type, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_appointment_type_display()
        )
    appointment_type_badge.short_description = 'Type'
    
    def status_badge(self, obj):
        colors = {
            'scheduled': '#ffc107',
            'confirmed': '#28a745',
            'completed': '#17a2b8',
            'cancelled': '#dc3545',
            'no_show': '#6c757d',
            'rescheduled': '#fd7e14'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Statut'
    
    def reminder_status(self, obj):
        if obj.reminder_sent:
            return format_html('<span style="color: green;">✓ Envoyé le {}</span>', obj.reminder_sent_at.strftime('%d/%m %H:%M'))
        return format_html('<span style="color: orange;">Pas encore envoyé</span>')
    reminder_status.short_description = 'Rappel'
    
    actions = ['mark_as_completed', 'send_reminder']
    
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, f'{updated} rendez-vous marqué(s) comme effectué(s).')
    mark_as_completed.short_description = 'Marquer comme effectué'


@admin.register(PatientMessage)
class PatientMessageAdmin(admin.ModelAdmin):
    """Admin pour les messages patient"""
    list_display = [
        'created_at', 'patient', 'subject',
        'message_type_badge', 'priority_badge',
        'status_badge', 'assigned_to',
        'responded_at'
    ]
    list_filter = ['message_type', 'priority', 'status', 'created_at']
    search_fields = ['patient__first_name', 'patient__last_name', 'subject', 'message']
    autocomplete_fields = ['pharmacie', 'patient', 'assigned_to', 'responded_by']
    readonly_fields = ['created_at', 'updated_at']
    
    def message_type_badge(self, obj):
        colors = {
            'question': '#007bff',
            'complaint': '#dc3545',
            'feedback': '#28a745',
            'appointment_request': '#ffc107',
            'renewal_request': '#17a2b8',
        }
        color = colors.get(obj.message_type, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_message_type_display()
        )
    message_type_badge.short_description = 'Type'
    
    def priority_badge(self, obj):
        colors = {'low': '#28a745', 'normal': '#007bff', 'high': '#fd7e14', 'urgent': '#dc3545'}
        icons = {'low': '●', 'normal': '●●', 'high': '●●●', 'urgent': '🚨'}
        color = colors.get(obj.priority, '#6c757d')
        icon = icons.get(obj.priority, '●')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_priority_display()
        )
    priority_badge.short_description = 'Priorité'
    
    def status_badge(self, obj):
        colors = {'new': '#ffc107', 'in_progress': '#007bff', 'answered': '#28a745', 'closed': '#6c757d'}
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Statut'


# ============================================================================
# ADMIN PROGRAMME FIDÉLITÉ
# ============================================================================

@admin.register(LoyaltyTier)
class LoyaltyTierAdmin(admin.ModelAdmin):
    """Admin pour les niveaux de fidélité"""
    list_display = [
        'name', 'program', 'level_badge',
        'min_points', 'points_multiplier_display',
        'discount_percentage', 'customers_count',
        'is_active_badge'
    ]
    list_filter = ['program', 'is_active', 'level']
    search_fields = ['name', 'description', 'program__name']
    autocomplete_fields = ['program']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Niveau', {
            'fields': ('program', 'name', 'description', 'level')
        }),
        ('Seuils', {
            'fields': ('min_points', 'min_purchases', 'min_amount_spent')
        }),
        ('Avantages', {
            'fields': ('points_multiplier', 'discount_percentage')
        }),
        ('Apparence', {
            'fields': ('color',)
        }),
        ('Statut', {
            'fields': ('is_active',)
        }),
        ('Métadonnées', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    
    def level_badge(self, obj):
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 15px; border-radius: 3px; font-weight: bold; font-size: 12px;">Niveau {} - {}</span>',
            obj.color, obj.level, obj.name
        )
    level_badge.short_description = 'Niveau'
    
    def points_multiplier_display(self, obj):
        return format_html('<strong style="color: #28a745;">×{}</strong>', obj.points_multiplier)
    points_multiplier_display.short_description = 'Multiplicateur'
    
    def customers_count(self, obj):
        count = obj.customers.filter(is_active=True).count()
        return format_html('<strong style="color: #007bff;">{} client(s)</strong>', count)
    customers_count.short_description = 'Clients'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Actif</span>')
        return format_html('<span style="color: red;">✗ Inactif</span>')
    is_active_badge.short_description = 'Statut'


class LoyaltyTierInline(admin.TabularInline):
    """Inline pour les niveaux de fidélité"""
    model = LoyaltyTier
    extra = 1
    fields = ['name', 'level', 'min_points', 'points_multiplier', 'discount_percentage', 'color', 'is_active']


@admin.register(LoyaltyProgram)
class LoyaltyProgramAdmin(admin.ModelAdmin):
    """Admin pour le programme de fidélité"""
    list_display = [
        'name', 'pharmacie', 'points_per_xaf',
        'enable_tiers_badge', 'total_members',
        'is_active_badge'
    ]
    list_filter = ['is_active', 'enable_tiers']
    search_fields = ['name', 'pharmacie__name']
    autocomplete_fields = ['pharmacie']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [LoyaltyTierInline]
    
    def enable_tiers_badge(self, obj):
        if obj.enable_tiers:
            return format_html('<span style="color: green;">✓ Niveaux activés</span>')
        return format_html('<span style="color: #6c757d;">Niveaux désactivés</span>')
    enable_tiers_badge.short_description = 'Niveaux'
    
    def total_members(self, obj):
        count = obj.customer_accounts.filter(is_active=True).count()
        return format_html('<strong style="color: #007bff;">{} membres</strong>', count)
    total_members.short_description = 'Membres'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green; font-size: 16px;">✓ Actif</span>')
        return format_html('<span style="color: red; font-size: 16px;">✗ Inactif</span>')
    is_active_badge.short_description = 'Statut'


class LoyaltyTransactionInline(admin.TabularInline):
    """Inline pour les transactions de fidélité"""
    model = LoyaltyTransaction
    extra = 0
    fields = ['transaction_date', 'transaction_type', 'points', 'description', 'expires_at']
    readonly_fields = ['transaction_date', 'created_at']
    can_delete = False
    max_num = 10
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(CustomerLoyalty)
class CustomerLoyaltyAdmin(admin.ModelAdmin):
    """Admin pour les comptes fidélité client"""
    list_display = [
        'customer', 'program', 'tier_badge',
        'points_balance_display', 'total_purchases_display',
        'last_activity_date', 'is_active_badge'
    ]
    list_filter = ['program', 'current_tier', 'is_active', 'enrolled_date']
    search_fields = ['customer__first_name', 'customer__last_name']
    autocomplete_fields = ['customer', 'program', 'current_tier']
    readonly_fields = ['created_at', 'updated_at', 'enrolled_date']
    inlines = [LoyaltyTransactionInline]
    
    def tier_badge(self, obj):
        if obj.current_tier:
            return format_html(
                '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
                obj.current_tier.color, obj.current_tier.name
            )
        return format_html('<span style="color: #6c757d;">Aucun niveau</span>')
    tier_badge.short_description = 'Niveau'
    
    def points_balance_display(self, obj):
        return format_html(
            '<strong style="color: #28a745; font-size: 14px;">{:,} pts</strong><br/>'
            '<small>Gagnés: {:,} | Utilisés: {:,} | Expirés: {:,}</small>',
            obj.points_balance, obj.total_points_earned, obj.points_used, obj.points_expired
        )
    points_balance_display.short_description = 'Points'
    
    def total_purchases_display(self, obj):
        return format_html(
            '<strong>{}</strong> achats<br/>'
            '<small style="color: #28a745;">{:,.0f} XAF</small>',
            obj.total_purchases, obj.total_amount_spent
        )
    total_purchases_display.short_description = 'Achats'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Actif</span>')
        return format_html('<span style="color: red;">✗ Inactif</span>')
    is_active_badge.short_description = 'Statut'


# ============================================================================
# ADMIN MARKETING & CRM
# ============================================================================

@admin.register(MarketingCampaign)
class MarketingCampaignAdmin(admin.ModelAdmin):
    """Admin pour les campagnes marketing"""
    list_display = [
        'name', 'campaign_type_badge', 'status_badge',
        'scheduled_datetime', 'stats_display',
        'roi_display', 'created_at'
    ]
    list_filter = ['campaign_type', 'status', 'scheduled_datetime']
    search_fields = ['name', 'subject']
    autocomplete_fields = ['pharmacie', 'created_by']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Identification', {
            'fields': ('pharmacie', 'name', 'description', 'campaign_type')
        }),
        ('Contenu', {
            'fields': ('subject', 'message_body', 'target_segment')
        }),
        ('Planification', {
            'fields': ('scheduled_datetime', 'start_datetime', 'end_datetime')
        }),
        ('Statut', {
            'fields': ('status',)
        }),
        ('Statistiques', {
            'fields': (
                'total_recipients', 'total_sent', 'total_delivered',
                'total_opened', 'total_clicked', 'total_conversions'
            ),
            'classes': ('collapse',)
        }),
        ('ROI', {
            'fields': ('campaign_cost', 'revenue_generated')
        })
    )
    
    def campaign_type_badge(self, obj):
        colors = {'email': '#007bff', 'sms': '#28a745', 'push': '#ffc107', 'social': '#17a2b8', 'mixed': '#6c757d'}
        icons = {'email': '📧', 'sms': '📱', 'push': '🔔', 'social': '👥', 'mixed': '📢'}
        color = colors.get(obj.campaign_type, '#6c757d')
        icon = icons.get(obj.campaign_type, '●')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px;">{} {}</span>',
            color, icon, obj.get_campaign_type_display()
        )
    campaign_type_badge.short_description = 'Type'
    
    def status_badge(self, obj):
        colors = {
            'draft': '#6c757d', 'scheduled': '#ffc107', 'running': '#28a745',
            'completed': '#17a2b8', 'paused': '#fd7e14', 'cancelled': '#dc3545'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Statut'
    
    def stats_display(self, obj):
        if obj.total_sent > 0:
            open_rate = (obj.total_opened / obj.total_sent * 100)
            click_rate = (obj.total_clicked / obj.total_sent * 100)
            conv_rate = (obj.total_conversions / obj.total_sent * 100)
            return format_html(
                '<small>Envois: <strong>{}</strong><br/>'
                'Ouverture: <strong style="color: #007bff;">{:.1f}%</strong><br/>'
                'Clic: <strong style="color: #28a745;">{:.1f}%</strong><br/>'
                'Conversion: <strong style="color: #dc3545;">{:.1f}%</strong></small>',
                obj.total_sent, open_rate, click_rate, conv_rate
            )
        return '-'
    stats_display.short_description = 'Statistiques'
    
    def roi_display(self, obj):
        roi = obj.calculate_roi()
        color = '#28a745' if roi > 0 else '#dc3545'
        return format_html(
            '<strong style="color: {}; font-size: 14px;">{:+.1f}%</strong><br/>'
            '<small>Coût: {:,.0f} | Revenus: {:,.0f}</small>',
            color, roi, obj.campaign_cost, obj.revenue_generated
        )
    roi_display.short_description = 'ROI'
    
    actions = ['launch_campaign', 'pause_campaign']
    
    def launch_campaign(self, request, queryset):
        updated = queryset.update(status='running', start_datetime=timezone.now())
        self.message_user(request, f'{updated} campagne(s) lancée(s).')
    launch_campaign.short_description = 'Lancer la campagne'
    
    def pause_campaign(self, request, queryset):
        updated = queryset.update(status='paused')
        self.message_user(request, f'{updated} campagne(s) mise(s) en pause.')
    pause_campaign.short_description = 'Mettre en pause'


@admin.register(CampaignRecipient)
class CampaignRecipientAdmin(admin.ModelAdmin):
    """Admin pour les destinataires de campagne"""
    list_display = [
        'customer', 'campaign', 'status_badge',
        'sent_at', 'opened_at', 'clicked_at',
        'converted_badge', 'created_at'
    ]
    list_filter = ['status', 'converted', 'campaign', 'sent_at']
    search_fields = ['customer__first_name', 'customer__last_name', 'customer__email', 'campaign__name']
    autocomplete_fields = ['campaign', 'customer']
    readonly_fields = ['sent_at', 'delivered_at', 'opened_at', 'clicked_at', 'created_at']
    
    fieldsets = (
        ('Campagne et Client', {
            'fields': ('campaign', 'customer')
        }),
        ('Statut', {
            'fields': ('status',)
        }),
        ('Dates de suivi', {
            'fields': ('sent_at', 'delivered_at', 'opened_at', 'clicked_at')
        }),
        ('Conversion', {
            'fields': ('converted', 'conversion_amount')
        }),
        ('Métadonnées', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    
    def status_badge(self, obj):
        colors = {
            'pending': '#6c757d', 'sent': '#007bff', 'delivered': '#17a2b8',
            'opened': '#28a745', 'clicked': '#ffc107', 'converted': '#e83e8c',
            'bounced': '#dc3545', 'unsubscribed': '#6c757d'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Statut'
    
    def converted_badge(self, obj):
        if obj.converted:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Converti</span><br/>'
                '<small style="color: #28a745;">{:,.0f} XAF</small>',
                obj.conversion_amount
            )
        return format_html('<span style="color: #6c757d;">-</span>')
    converted_badge.short_description = 'Conversion'


@admin.register(LoyaltyTransaction)
class LoyaltyTransactionAdmin(admin.ModelAdmin):
    """Admin pour les transactions de fidélité"""
    list_display = [
        'transaction_date', 'customer_display', 'transaction_type_badge',
        'points_display', 'sale', 'expires_at', 'created_at'
    ]
    list_filter = ['transaction_type', 'transaction_date', 'customer_loyalty__program']
    search_fields = [
        'customer_loyalty__customer__first_name',
        'customer_loyalty__customer__last_name',
        'description',
        'sale__sale_number'
    ]
    autocomplete_fields = ['customer_loyalty', 'sale']
    readonly_fields = ['transaction_date', 'created_at']
    
    fieldsets = (
        ('Transaction', {
            'fields': ('customer_loyalty', 'transaction_type', 'points')
        }),
        ('Référence', {
            'fields': ('sale', 'description')
        }),
        ('Expiration', {
            'fields': ('expires_at',)
        }),
        ('Métadonnées', {
            'fields': ('transaction_date', 'created_at'),
            'classes': ('collapse',)
        })
    )
    
    def customer_display(self, obj):
        return obj.customer_loyalty.customer.get_full_name()
    customer_display.short_description = 'Client'
    
    def transaction_type_badge(self, obj):
        colors = {
            'earn': '#28a745',
            'redeem': '#dc3545',
            'expire': '#6c757d',
            'bonus': '#ffc107',
            'adjustment': '#17a2b8',
            'refund': '#fd7e14',
        }
        icons = {
            'earn': '+',
            'redeem': '-',
            'expire': '⏱️',
            'bonus': '🎁',
            'adjustment': '⚙️',
            'refund': '↩️',
        }
        color = colors.get(obj.transaction_type, '#6c757d')
        icon = icons.get(obj.transaction_type, '●')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px;">{} {}</span>',
            color, icon, obj.get_transaction_type_display()
        )
    transaction_type_badge.short_description = 'Type'
    
    def points_display(self, obj):
        color = '#28a745' if obj.points > 0 else '#dc3545'
        sign = '+' if obj.points > 0 else ''
        return format_html(
            '<strong style="color: {}; font-size: 14px;">{}{}</strong>',
            color, sign, obj.points
        )
    points_display.short_description = 'Points'


@admin.register(CustomerSegment)
class CustomerSegmentAdmin(admin.ModelAdmin):
    """Admin pour les segments de clientèle"""
    list_display = [
        'name', 'pharmacie', 'customer_count_display',
        'is_dynamic_badge', 'last_calculated_at',
        'is_active_badge', 'created_at'
    ]
    list_filter = ['is_dynamic', 'is_active', 'gender', 'pharmacie']
    search_fields = ['name', 'description', 'pharmacie__name']
    autocomplete_fields = ['pharmacie', 'loyalty_tier']
    readonly_fields = ['customer_count', 'last_calculated_at', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Identification', {
            'fields': ('pharmacie', 'name', 'description')
        }),
        ('Critères démographiques', {
            'fields': ('age_min', 'age_max', 'gender', 'city')
        }),
        ('Critères d\'achat', {
            'fields': ('min_purchases', 'min_amount_spent', 'days_since_last_purchase')
        }),
        ('Critères fidélité', {
            'fields': ('loyalty_tier',)
        }),
        ('Configuration', {
            'fields': ('is_dynamic', 'is_active')
        }),
        ('Statistiques', {
            'fields': ('customer_count', 'last_calculated_at'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def customer_count_display(self, obj):
        return format_html('<strong style="color: #007bff; font-size: 14px;">{} client(s)</strong>', obj.customer_count)
    customer_count_display.short_description = 'Clients'
    
    def is_dynamic_badge(self, obj):
        if obj.is_dynamic:
            return format_html('<span style="background: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">🔄 Dynamique</span>')
        return format_html('<span style="background: #6c757d; color: white; padding: 3px 10px; border-radius: 3px;">📌 Statique</span>')
    is_dynamic_badge.short_description = 'Type'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Actif</span>')
        return format_html('<span style="color: red;">✗ Inactif</span>')
    is_active_badge.short_description = 'Statut'
    
    actions = ['recalculate_segments']
    
    def recalculate_segments(self, request, queryset):
        # TODO: Implémenter la logique de recalcul
        self.message_user(request, f'{queryset.count()} segment(s) en cours de recalcul.')
    recalculate_segments.short_description = 'Recalculer les segments'


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    """Admin pour les leads"""
    list_display = [
        'created_at', 'get_full_name', 'source_badge',
        'status_badge', 'assigned_to',
        'interest_area', 'conversion_display'
    ]
    list_filter = ['source', 'status', 'created_at']
    search_fields = ['first_name', 'last_name', 'email', 'phone']
    autocomplete_fields = ['pharmacie', 'assigned_to', 'converted_to_customer']
    readonly_fields = ['created_at', 'updated_at', 'converted_at']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    get_full_name.short_description = 'Nom'
    
    def source_badge(self, obj):
        colors = {
            'website': '#007bff', 'social_media': '#17a2b8', 'referral': '#28a745',
            'walk_in': '#ffc107', 'phone': '#fd7e14', 'email': '#6c757d'
        }
        icons = {
            'website': '🌐', 'social_media': '👥', 'referral': '👤',
            'walk_in': '🚶', 'phone': '📞', 'email': '📧'
        }
        color = colors.get(obj.source, '#6c757d')
        icon = icons.get(obj.source, '●')
        return format_html(
            '<span style="color: {};">{} {}</span>',
            color, icon, obj.get_source_display()
        )
    source_badge.short_description = 'Source'
    
    def status_badge(self, obj):
        colors = {
            'new': '#ffc107', 'contacted': '#007bff', 'qualified': '#17a2b8',
            'converted': '#28a745', 'lost': '#dc3545'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Statut'
    
    def conversion_display(self, obj):
        if obj.converted_to_customer:
            return format_html(
                '<span style="color: green;">✓ Converti le {}</span>',
                obj.converted_at.strftime('%d/%m/%Y')
            )
        return '-'
    conversion_display.short_description = 'Conversion'
    
    actions = ['mark_as_contacted', 'mark_as_converted']
    
    def mark_as_contacted(self, request, queryset):
        updated = queryset.update(status='contacted')
        self.message_user(request, f'{updated} lead(s) marqué(s) comme contacté(s).')
    mark_as_contacted.short_description = 'Marquer comme contacté'


@admin.register(AutomatedReminder)
class AutomatedReminderAdmin(admin.ModelAdmin):
    """Admin pour les rappels automatiques"""
    list_display = [
        'scheduled_datetime', 'customer', 'reminder_type_badge',
        'send_methods', 'status_badge', 'sent_at'
    ]
    list_filter = ['reminder_type', 'status', 'scheduled_datetime']
    search_fields = ['customer__first_name', 'customer__last_name', 'message']
    autocomplete_fields = ['pharmacie', 'customer', 'treatment', 'appointment']
    readonly_fields = ['created_at', 'sent_at']
    
    def reminder_type_badge(self, obj):
        colors = {
            'medication_renewal': '#28a745', 'appointment': '#007bff',
            'medication_time': '#ffc107', 'birthday': '#e83e8c',
            'inactive_customer': '#fd7e14', 'loyalty_points': '#17a2b8'
        }
        icons = {
            'medication_renewal': '💊', 'appointment': '📅',
            'medication_time': '⏰', 'birthday': '🎂',
            'inactive_customer': '💤', 'loyalty_points': '⭐'
        }
        color = colors.get(obj.reminder_type, '#6c757d')
        icon = icons.get(obj.reminder_type, '🔔')
        return format_html(
            '<span style="color: {};">{} {}</span>',
            color, icon, obj.get_reminder_type_display()
        )
    reminder_type_badge.short_description = 'Type'
    
    def send_methods(self, obj):
        methods = []
        if obj.send_via_sms:
            methods.append('<span style="color: #28a745;">📱 SMS</span>')
        if obj.send_via_email:
            methods.append('<span style="color: #007bff;">📧 Email</span>')
        if obj.send_via_push:
            methods.append('<span style="color: #ffc107;">🔔 Push</span>')
        return format_html(' '.join(methods)) if methods else '-'
    send_methods.short_description = 'Méthodes'
    
    def status_badge(self, obj):
        colors = {'pending': '#ffc107', 'sent': '#28a745', 'failed': '#dc3545', 'cancelled': '#6c757d'}
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Statut'


