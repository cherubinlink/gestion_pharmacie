"""
Serializers pour le Suivi Médical & CRM Marketing
API REST complète avec statistiques et analytics
Applications 7 & 8
"""
from rest_framework import serializers
from django.db.models import Count, Sum, Avg, Q, F
from datetime import timedelta
from django.utils import timezone
from decimal import Decimal

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



# ============================================================================
# SERIALIZERS MÉDECINS ET PROFILS MÉDICAUX
# ============================================================================

class DoctorSerializer(serializers.ModelSerializer):
    """Serializer pour les médecins"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    speciality_display = serializers.CharField(source='get_speciality_display', read_only=True)
    pharmacie_name = serializers.CharField(source='pharmacie.name', read_only=True)
    
    # Statistiques
    total_patients = serializers.SerializerMethodField()
    total_prescriptions = serializers.SerializerMethodField()
    
    class Meta:
        model = Doctor
        fields = [
            'id', 'pharmacie', 'pharmacie_name', 'doctor_code',
            'first_name', 'last_name', 'title', 'full_name',
            'speciality', 'speciality_display',
            'phone', 'mobile', 'email',
            'address', 'city',
            'license_number', 'hospital',
            'is_active', 'notes',
            'total_patients', 'total_prescriptions',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'doctor_code', 'created_at', 'updated_at']
    
    def get_total_patients(self, obj):
        """Nombre total de patients"""
        return obj.patient_links.filter(is_active=True).count()
    
    def get_total_prescriptions(self, obj):
        """Nombre total d'ordonnances"""
        return obj.prescriptions.count()


class MedicalProfileSerializer(serializers.ModelSerializer):
    """Serializer pour les profils médicaux"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    primary_doctor_name = serializers.CharField(source='primary_doctor.get_full_name', read_only=True)
    bmi = serializers.SerializerMethodField()
    
    class Meta:
        model = MedicalProfile
        fields = [
            'id', 'patient', 'patient_name',
            'blood_type', 'height', 'weight', 'bmi',
            'primary_doctor', 'primary_doctor_name',
            'emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relation',
            'insurance_provider', 'insurance_number',
            'consent_data_usage', 'consent_communication',
            'medical_notes', 'last_checkup_date',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_bmi(self, obj):
        """Calcule l'IMC"""
        return obj.calculate_bmi()


class DoctorPatientLinkSerializer(serializers.ModelSerializer):
    """Serializer pour les liens médecin-patient"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)
    relation_type_display = serializers.CharField(source='get_relation_type_display', read_only=True)
    
    class Meta:
        model = DoctorPatientLink
        fields = [
            'id', 'patient', 'patient_name', 'doctor', 'doctor_name',
            'is_primary', 'relation_type', 'relation_type_display',
            'start_date', 'end_date', 'is_active', 'notes',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


# ============================================================================
# SERIALIZERS PATHOLOGIES ET ALLERGIES
# ============================================================================

class MedicalConditionSerializer(serializers.ModelSerializer):
    """Serializer pour les pathologies"""
    condition_type_display = serializers.CharField(source='get_condition_type_display', read_only=True)
    total_cases = serializers.SerializerMethodField()
    
    class Meta:
        model = MedicalCondition
        fields = [
            'id', 'code', 'name',
            'condition_type', 'condition_type_display',
            'description', 'symptoms', 'category',
            'is_active', 'total_cases',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_total_cases(self, obj):
        """Nombre de cas actifs"""
        return obj.patient_cases.filter(status='active').count()


class PatientConditionSerializer(serializers.ModelSerializer):
    """Serializer pour les pathologies patient"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    condition_name = serializers.CharField(source='condition.name', read_only=True)
    condition_code = serializers.CharField(source='condition.code', read_only=True)
    diagnosed_by_name = serializers.CharField(source='diagnosed_by.get_full_name', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = PatientCondition
        fields = [
            'id', 'patient', 'patient_name',
            'condition', 'condition_name', 'condition_code',
            'diagnosis_date', 'resolved_date',
            'severity', 'severity_display',
            'status', 'status_display',
            'diagnosed_by', 'diagnosed_by_name',
            'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AllergenSerializer(serializers.ModelSerializer):
    """Serializer pour les allergènes"""
    allergen_type_display = serializers.CharField(source='get_allergen_type_display', read_only=True)
    total_cases = serializers.SerializerMethodField()
    
    class Meta:
        model = Allergen
        fields = [
            'id', 'name',
            'allergen_type', 'allergen_type_display',
            'active_substance', 'description', 'common_reactions',
            'is_active', 'total_cases',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_total_cases(self, obj):
        """Nombre de cas actifs"""
        return obj.patient_cases.filter(is_active=True).count()


class PatientAllergySerializer(serializers.ModelSerializer):
    """Serializer pour les allergies patient"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    allergen_name = serializers.CharField(source='allergen.name', read_only=True)
    diagnosed_by_name = serializers.CharField(source='diagnosed_by.get_full_name', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    reaction_type_display = serializers.CharField(source='get_reaction_type_display', read_only=True)
    
    class Meta:
        model = PatientAllergy
        fields = [
            'id', 'patient', 'patient_name',
            'allergen', 'allergen_name',
            'severity', 'severity_display',
            'reaction_type', 'reaction_type_display',
            'symptoms',
            'first_occurrence_date', 'last_occurrence_date',
            'diagnosed_by', 'diagnosed_by_name',
            'is_active', 'notes', 'emergency_instructions',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# SERIALIZERS ORDONNANCES ET TRAITEMENTS
# ============================================================================

class PrescriptionItemSerializer(serializers.ModelSerializer):
    """Serializer pour les lignes d'ordonnance"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = PrescriptionItem
        fields = [
            'id', 'prescription', 'product', 'product_name',
            'quantity', 'dosage', 'frequency', 'duration',
            'instructions', 'substitution_allowed',
            'quantity_dispensed',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PrescriptionSerializer(serializers.ModelSerializer):
    """Serializer pour les ordonnances"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)
    dispensed_by_name = serializers.CharField(source='dispensed_by.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_expired = serializers.SerializerMethodField()
    items = PrescriptionItemSerializer(many=True, read_only=True)
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Prescription
        fields = [
            'id', 'prescription_number',
            'patient', 'patient_name',
            'doctor', 'doctor_name',
            'prescription_date', 'expiry_date',
            'diagnosis',
            'status', 'status_display',
            'is_renewable', 'renewal_count', 'renewals_remaining',
            'prescription_file', 'notes', 'pharmacist_notes',
            'dispensed_at', 'dispensed_by', 'dispensed_by_name',
            'is_expired', 'items', 'items_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'prescription_number', 'created_at', 'updated_at']
    
    def get_is_expired(self, obj):
        """Vérifie si expiré"""
        return obj.is_expired()
    
    def get_items_count(self, obj):
        """Nombre de lignes"""
        return obj.items.count()


class TreatmentMedicationSerializer(serializers.ModelSerializer):
    """Serializer pour les médicaments du traitement"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = TreatmentMedication
        fields = [
            'id', 'treatment', 'product', 'product_name',
            'dosage', 'frequency', 'instructions',
            'start_date', 'end_date', 'is_active',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TreatmentSerializer(serializers.ModelSerializer):
    """Serializer pour les traitements"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    condition_name = serializers.CharField(source='condition.condition.name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    medications = TreatmentMedicationSerializer(many=True, read_only=True)
    
    class Meta:
        model = Treatment
        fields = [
            'id', 'patient', 'patient_name',
            'name', 'description',
            'condition', 'condition_name',
            'prescription',
            'start_date', 'end_date', 'actual_end_date',
            'status', 'status_display',
            'doctor', 'doctor_name',
            'reminder_enabled', 'reminder_frequency',
            'notes', 'medications',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# SERIALIZERS DME ET INTERACTIONS
# ============================================================================

class ExternalMedicalRecordSerializer(serializers.ModelSerializer):
    """Serializer pour les dossiers médicaux externes"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)
    verified_by_name = serializers.CharField(source='verified_by.get_full_name', read_only=True)
    record_type_display = serializers.CharField(source='get_record_type_display', read_only=True)
    source_system_display = serializers.CharField(source='get_source_system_display', read_only=True)
    
    class Meta:
        model = ExternalMedicalRecord
        fields = [
            'id', 'patient', 'patient_name',
            'external_id',
            'record_type', 'record_type_display',
            'source_system', 'source_system_display', 'source_name',
            'title', 'content',
            'doctor', 'doctor_name',
            'document_file',
            'record_date', 'import_date',
            'fhir_resource_type', 'fhir_resource_id',
            'is_verified', 'verified_by', 'verified_by_name', 'verified_at',
            'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'import_date', 'created_at', 'updated_at']


class AppointmentSerializer(serializers.ModelSerializer):
    """Serializer pour les rendez-vous"""
    pharmacie_name = serializers.CharField(source='pharmacie.name', read_only=True)
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    pharmacist_name = serializers.CharField(source='pharmacist.get_full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    appointment_type_display = serializers.CharField(source='get_appointment_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'pharmacie', 'pharmacie_name',
            'patient', 'patient_name',
            'appointment_type', 'appointment_type_display',
            'reason',
            'appointment_datetime', 'duration_minutes',
            'pharmacist', 'pharmacist_name',
            'status', 'status_display',
            'reminder_sent', 'reminder_sent_at',
            'notes', 'completion_notes',
            'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PatientMessageSerializer(serializers.ModelSerializer):
    """Serializer pour les messages patient"""
    pharmacie_name = serializers.CharField(source='pharmacie.name', read_only=True)
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    responded_by_name = serializers.CharField(source='responded_by.get_full_name', read_only=True)
    message_type_display = serializers.CharField(source='get_message_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    
    class Meta:
        model = PatientMessage
        fields = [
            'id', 'pharmacie', 'pharmacie_name',
            'patient', 'patient_name',
            'message_type', 'message_type_display',
            'subject', 'message',
            'priority', 'priority_display',
            'status', 'status_display',
            'assigned_to', 'assigned_to_name',
            'response', 'responded_at', 'responded_by', 'responded_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# SERIALIZERS PROGRAMME FIDÉLITÉ
# ============================================================================

class LoyaltyTierSerializer(serializers.ModelSerializer):
    """Serializer pour les niveaux de fidélité"""
    customers_count = serializers.SerializerMethodField()
    
    class Meta:
        model = LoyaltyTier
        fields = [
            'id', 'program', 'name', 'description',
            'min_points', 'min_purchases', 'min_amount_spent',
            'points_multiplier', 'discount_percentage',
            'level', 'color', 'is_active',
            'customers_count',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_customers_count(self, obj):
        """Nombre de clients au niveau"""
        return obj.customers.filter(is_active=True).count()


class LoyaltyProgramSerializer(serializers.ModelSerializer):
    """Serializer pour le programme de fidélité"""
    pharmacie_name = serializers.CharField(source='pharmacie.name', read_only=True)
    tiers = LoyaltyTierSerializer(many=True, read_only=True)
    total_members = serializers.SerializerMethodField()
    
    class Meta:
        model = LoyaltyProgram
        fields = [
            'id', 'pharmacie', 'pharmacie_name',
            'name', 'description',
            'points_per_xaf', 'points_expiry_months',
            'min_points_redemption', 'xaf_per_point',
            'birthday_bonus_points', 'referral_bonus_points',
            'enable_tiers', 'is_active',
            'tiers', 'total_members',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_total_members(self, obj):
        """Nombre total de membres"""
        return obj.customer_accounts.filter(is_active=True).count()


class LoyaltyTransactionSerializer(serializers.ModelSerializer):
    """Serializer pour les transactions de fidélité"""
    customer_name = serializers.CharField(source='customer_loyalty.customer.get_full_name', read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    sale_number = serializers.CharField(source='sale.sale_number', read_only=True)
    
    class Meta:
        model = LoyaltyTransaction
        fields = [
            'id', 'customer_loyalty', 'customer_name',
            'transaction_type', 'transaction_type_display',
            'points', 'sale', 'sale_number',
            'description', 'expires_at',
            'transaction_date', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class CustomerLoyaltySerializer(serializers.ModelSerializer):
    """Serializer pour le compte fidélité client"""
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    program_name = serializers.CharField(source='program.name', read_only=True)
    current_tier_name = serializers.CharField(source='current_tier.name', read_only=True)
    recent_transactions = LoyaltyTransactionSerializer(source='transactions', many=True, read_only=True)
    
    class Meta:
        model = CustomerLoyalty
        fields = [
            'id', 'customer', 'customer_name',
            'program', 'program_name',
            'total_points_earned', 'points_balance', 'points_used', 'points_expired',
            'current_tier', 'current_tier_name',
            'total_purchases', 'total_amount_spent',
            'enrolled_date', 'last_activity_date', 'is_active',
            'recent_transactions',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# SERIALIZERS MARKETING & CRM
# ============================================================================

class CampaignRecipientSerializer(serializers.ModelSerializer):
    """Serializer pour les destinataires de campagne"""
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    customer_email = serializers.EmailField(source='customer.email', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = CampaignRecipient
        fields = [
            'id', 'campaign', 'customer', 'customer_name', 'customer_email', 'customer_phone',
            'status', 'status_display',
            'sent_at', 'delivered_at', 'opened_at', 'clicked_at',
            'converted', 'conversion_amount',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class MarketingCampaignSerializer(serializers.ModelSerializer):
    """Serializer pour les campagnes marketing"""
    pharmacie_name = serializers.CharField(source='pharmacie.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    campaign_type_display = serializers.CharField(source='get_campaign_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    roi = serializers.SerializerMethodField()
    open_rate = serializers.SerializerMethodField()
    click_rate = serializers.SerializerMethodField()
    conversion_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = MarketingCampaign
        fields = [
            'id', 'pharmacie', 'pharmacie_name',
            'name', 'description',
            'campaign_type', 'campaign_type_display',
            'subject', 'message_body', 'target_segment',
            'scheduled_datetime', 'start_datetime', 'end_datetime',
            'status', 'status_display',
            'total_recipients', 'total_sent', 'total_delivered',
            'total_opened', 'total_clicked', 'total_conversions',
            'campaign_cost', 'revenue_generated',
            'roi', 'open_rate', 'click_rate', 'conversion_rate',
            'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_roi(self, obj):
        """ROI de la campagne"""
        return float(obj.calculate_roi())
    
    def get_open_rate(self, obj):
        """Taux d'ouverture"""
        if obj.total_sent > 0:
            return (obj.total_opened / obj.total_sent) * 100
        return 0
    
    def get_click_rate(self, obj):
        """Taux de clic"""
        if obj.total_opened > 0:
            return (obj.total_clicked / obj.total_opened) * 100
        return 0
    
    def get_conversion_rate(self, obj):
        """Taux de conversion"""
        if obj.total_sent > 0:
            return (obj.total_conversions / obj.total_sent) * 100
        return 0


class CustomerSegmentSerializer(serializers.ModelSerializer):
    """Serializer pour les segments de clientèle"""
    pharmacie_name = serializers.CharField(source='pharmacie.name', read_only=True)
    loyalty_tier_name = serializers.CharField(source='loyalty_tier.name', read_only=True)
    
    class Meta:
        model = CustomerSegment
        fields = [
            'id', 'pharmacie', 'pharmacie_name',
            'name', 'description',
            'age_min', 'age_max', 'gender',
            'min_purchases', 'min_amount_spent', 'days_since_last_purchase',
            'city',
            'loyalty_tier', 'loyalty_tier_name',
            'is_dynamic', 'customer_count', 'last_calculated_at',
            'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'customer_count', 'last_calculated_at', 'created_at', 'updated_at']


class LeadSerializer(serializers.ModelSerializer):
    """Serializer pour les leads"""
    pharmacie_name = serializers.CharField(source='pharmacie.name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    converted_customer_name = serializers.CharField(source='converted_to_customer.get_full_name', read_only=True)
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Lead
        fields = [
            'id', 'pharmacie', 'pharmacie_name',
            'first_name', 'last_name', 'email', 'phone',
            'source', 'source_display', 'source_details',
            'interest_area',
            'status', 'status_display',
            'assigned_to', 'assigned_to_name',
            'converted_to_customer', 'converted_customer_name', 'converted_at',
            'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AutomatedReminderSerializer(serializers.ModelSerializer):
    """Serializer pour les rappels automatiques"""
    pharmacie_name = serializers.CharField(source='pharmacie.name', read_only=True)
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    treatment_name = serializers.CharField(source='treatment.name', read_only=True)
    reminder_type_display = serializers.CharField(source='get_reminder_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = AutomatedReminder
        fields = [
            'id', 'pharmacie', 'pharmacie_name',
            'customer', 'customer_name',
            'reminder_type', 'reminder_type_display',
            'message',
            'send_via_sms', 'send_via_email', 'send_via_push',
            'scheduled_datetime',
            'status', 'status_display', 'sent_at',
            'treatment', 'treatment_name', 'appointment',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


# ============================================================================
# SERIALIZERS STATISTIQUES ET ANALYTICS
# ============================================================================

class MedicalStatsSerializer(serializers.Serializer):
    """Statistiques médicales globales"""
    total_patients_with_profile = serializers.IntegerField()
    total_active_treatments = serializers.IntegerField()
    total_prescriptions_this_month = serializers.IntegerField()
    critical_allergies_count = serializers.IntegerField()
    pending_appointments = serializers.IntegerField()
    overdue_treatments = serializers.IntegerField()


class LoyaltyStatsSerializer(serializers.Serializer):
    """Statistiques programme fidélité"""
    total_members = serializers.IntegerField()
    active_members = serializers.IntegerField()
    total_points_distributed = serializers.IntegerField()
    total_points_redeemed = serializers.IntegerField()
    average_points_per_member = serializers.FloatField()
    tier_distribution = serializers.DictField()


class CampaignStatsSerializer(serializers.Serializer):
    """Statistiques campagnes marketing"""
    total_campaigns = serializers.IntegerField()
    active_campaigns = serializers.IntegerField()
    total_recipients = serializers.IntegerField()
    average_open_rate = serializers.FloatField()
    average_click_rate = serializers.FloatField()
    average_conversion_rate = serializers.FloatField()
    total_roi = serializers.FloatField()


class CRMDashboardSerializer(serializers.Serializer):
    """Dashboard CRM complet"""
    medical_stats = MedicalStatsSerializer()
    loyalty_stats = LoyaltyStatsSerializer()
    campaign_stats = CampaignStatsSerializer()
    total_leads = serializers.IntegerField()
    leads_converted_this_month = serializers.IntegerField()
    pending_reminders = serializers.IntegerField()
