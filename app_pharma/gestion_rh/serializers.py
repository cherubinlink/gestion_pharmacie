"""
Serializers pour le suivi, la performance et l'historique
"""
from rest_framework import serializers
from gestion_rh.models import (
    TimeEntry, WorkSession, Commission, Promotion,
    Warning, Training, PerformanceReview, PerformanceMetrics, Bonus
)


class TimeEntrySerializer(serializers.ModelSerializer):
    """Serializer pour les pointages"""
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    manual_entry_by_name = serializers.CharField(
        source='manual_entry_by.get_full_name',
        read_only=True
    )
    
    class Meta:
        model = TimeEntry
        fields = [
            'id', 'employee', 'employee_name', 'entry_type', 'timestamp',
            'method', 'location', 'device_info', 'is_manual',
            'manual_entry_by', 'manual_entry_by_name', 'manual_entry_reason',
            'notes', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class WorkSessionSerializer(serializers.ModelSerializer):
    """Serializer pour les sessions de travail"""
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    
    class Meta:
        model = WorkSession
        fields = [
            'id', 'employee', 'employee_name', 'date', 'clock_in',
            'clock_out', 'scheduled_start', 'scheduled_end',
            'actual_hours', 'break_duration', 'overtime_hours',
            'is_late', 'late_duration', 'is_complete', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'actual_hours', 'break_duration', 'overtime_hours',
            'is_late', 'late_duration', 'is_complete', 'created_at', 'updated_at'
        ]


class WorkSessionStatisticsSerializer(serializers.Serializer):
    """Serializer pour les statistiques de travail"""
    total_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_overtime = serializers.DecimalField(max_digits=10, decimal_places=2)
    late_count = serializers.IntegerField()
    average_late_duration = serializers.IntegerField()
    attendance_rate = serializers.DecimalField(max_digits=5, decimal_places=2)


class CommissionSerializer(serializers.ModelSerializer):
    """Serializer pour les commissions"""
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    created_by_name = serializers.CharField(
        source='created_by.get_full_name',
        read_only=True
    )
    
    class Meta:
        model = Commission
        fields = [
            'id', 'employee', 'employee_name', 'amount',
            'commission_type', 'description', 'calculation_basis',
            'period_start', 'period_end', 'is_paid', 'paid_date',
            'created_by', 'created_by_name', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PromotionSerializer(serializers.ModelSerializer):
    """Serializer pour les promotions"""
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    old_role_name = serializers.CharField(source='old_role.name', read_only=True)
    new_role_name = serializers.CharField(source='new_role.name', read_only=True)
    approved_by_name = serializers.CharField(
        source='approved_by.get_full_name',
        read_only=True
    )
    
    class Meta:
        model = Promotion
        fields = [
            'id', 'employee', 'employee_name', 'old_role', 'old_role_name',
            'new_role', 'new_role_name', 'old_salary', 'new_salary',
            'promotion_date', 'reason', 'approved_by', 'approved_by_name',
            'notes', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class WarningSerializer(serializers.ModelSerializer):
    """Serializer pour les avertissements"""
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    issued_by_name = serializers.CharField(
        source='issued_by.get_full_name',
        read_only=True
    )
    
    class Meta:
        model = Warning
        fields = [
            'id', 'employee', 'employee_name', 'severity', 'date_issued',
            'reason', 'description', 'action_taken', 'issued_by',
            'issued_by_name', 'documents', 'is_acknowledged',
            'acknowledged_at', 'employee_response', 'expiry_date',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TrainingSerializer(serializers.ModelSerializer):
    """Serializer pour les formations"""
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    
    class Meta:
        model = Training
        fields = [
            'id', 'employee', 'employee_name', 'title', 'description',
            'provider', 'start_date', 'end_date', 'duration_hours',
            'cost', 'status', 'certificate_obtained', 'certificate_url',
            'score', 'feedback', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PerformanceReviewSerializer(serializers.ModelSerializer):
    """Serializer pour les évaluations de performance"""
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    reviewer_name = serializers.CharField(
        source='reviewer.get_full_name',
        read_only=True
    )
    
    class Meta:
        model = PerformanceReview
        fields = [
            'id', 'employee', 'employee_name', 'review_period_start',
            'review_period_end', 'review_date', 'reviewer', 'reviewer_name',
            'overall_rating', 'criteria_scores', 'strengths',
            'areas_for_improvement', 'goals', 'employee_comments',
            'action_plan', 'next_review_date', 'documents',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_overall_rating(self, value):
        if value < 0 or value > 5:
            raise serializers.ValidationError(
                "La note globale doit être entre 0 et 5"
            )
        return value


class PerformanceMetricsSerializer(serializers.ModelSerializer):
    """Serializer pour les métriques de performance"""
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    
    class Meta:
        model = PerformanceMetrics
        fields = [
            'id', 'employee', 'employee_name', 'period_start', 'period_end',
            'total_sales', 'total_transactions', 'average_transaction_value',
            'punctuality_rate', 'attendance_rate', 'customer_satisfaction_score',
            'efficiency_score', 'custom_metrics', 'calculated_at'
        ]
        read_only_fields = ['id', 'calculated_at']


class BonusSerializer(serializers.ModelSerializer):
    """Serializer pour les primes"""
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(
        source='approved_by.get_full_name',
        read_only=True
    )
    
    class Meta:
        model = Bonus
        fields = [
            'id', 'employee', 'employee_name', 'bonus_type', 'amount',
            'description', 'calculation_basis', 'period_start',
            'period_end', 'is_paid', 'paid_date', 'approved_by',
            'approved_by_name', 'notes', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class EmployeeHistorySerializer(serializers.Serializer):
    """Serializer pour l'historique complet d'un employé"""
    commissions = CommissionSerializer(many=True, read_only=True)
    promotions = PromotionSerializer(many=True, read_only=True)
    warnings = WarningSerializer(many=True, read_only=True)
    trainings = TrainingSerializer(many=True, read_only=True)
    performance_reviews = PerformanceReviewSerializer(many=True, read_only=True)
    bonuses = BonusSerializer(many=True, read_only=True)


class DashboardStatisticsSerializer(serializers.Serializer):
    """Serializer pour les statistiques du tableau de bord"""
    total_employees = serializers.IntegerField()
    present_today = serializers.IntegerField()
    absent_today = serializers.IntegerField()
    late_today = serializers.IntegerField()
    on_leave = serializers.IntegerField()
    pending_leave_requests = serializers.IntegerField()
    pending_replacement_requests = serializers.IntegerField()
    average_attendance_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    average_punctuality_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
