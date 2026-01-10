"""
Configuration de l'interface d'administration Django
pour tous les modèles RH (Ressources Humaines)
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta
# Import de tous les modèles
from gestion_rh.models import (
    # Modèles de base
    Role, Employee, EmployeeTransferHistory,
    Client, ClientTransferHistory,
    
    # Planning et congés
    WorkSchedule, LeaveRequest, AbsenceRecord, ReplacementRequest,
    
    # Suivi et performance
    TimeEntry, WorkSession, Commission, Promotion,
    Warning, Training, PerformanceReview, PerformanceMetrics, Bonus
)


# Register your models here.

admin.site.site_header = "Administration RH Pharmacie"
admin.site.site_title = "RH Admin"
admin.site.index_title = "Gestion des Ressources Humaines"


# ============================================================================
# FILTRES PERSONNALISÉS
# ============================================================================

class ActiveEmployeeFilter(admin.SimpleListFilter):
    """Filtre pour les employés actifs"""
    title = 'Statut employé'
    parameter_name = 'is_active'
    
    def lookups(self, request, model_admin):
        return (
            ('active', 'Actifs uniquement'),
            ('on_leave', 'En congé'),
            ('all', 'Tous'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'active':
            return queryset.filter(employment_status='active')
        if self.value() == 'on_leave':
            return queryset.filter(employment_status='on_leave')
        return queryset


class DateRangeFilter(admin.SimpleListFilter):
    """Filtre par plage de dates"""
    title = 'Période'
    parameter_name = 'date_range'
    
    def lookups(self, request, model_admin):
        return (
            ('today', "Aujourd'hui"),
            ('week', 'Cette semaine'),
            ('month', 'Ce mois'),
            ('year', 'Cette année'),
        )
    
    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == 'today':
            return queryset.filter(created_at__date=now.date())
        elif self.value() == 'week':
            start = now - timedelta(days=now.weekday())
            return queryset.filter(created_at__gte=start)
        elif self.value() == 'month':
            return queryset.filter(created_at__year=now.year, created_at__month=now.month)
        elif self.value() == 'year':
            return queryset.filter(created_at__year=now.year)
        return queryset


# ============================================================================
# INLINE ADMIN
# ============================================================================

class EmployeeTransferHistoryInline(admin.TabularInline):
    """Inline pour l'historique des transferts d'employés"""
    model = EmployeeTransferHistory
    extra = 0
    readonly_fields = ['transfer_date', 'from_pharmacie', 'to_pharmacie', 'old_salary', 'new_salary']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


class WorkScheduleInline(admin.TabularInline):
    """Inline pour le planning de travail"""
    model = WorkSchedule
    extra = 0
    fields = ['date', 'shift_type', 'start_time', 'end_time', 'notes']
    readonly_fields = ['created_at']


class LeaveRequestInline(admin.TabularInline):
    """Inline pour les demandes de congés"""
    model = LeaveRequest
    extra = 0
    fields = ['leave_type', 'start_date', 'end_date', 'total_days', 'status']
    readonly_fields = ['created_at']


class TimeEntryInline(admin.TabularInline):
    """Inline pour les pointages"""
    model = TimeEntry
    extra = 0
    fields = ['entry_type', 'timestamp', 'method', 'is_manual']
    readonly_fields = ['timestamp', 'created_at']
    ordering = ['-timestamp']


# ============================================================================
# ADMIN - RÔLES ET EMPLOYÉS
# ============================================================================

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'pharmacie', 'is_default', 'employee_count', 'created_at']
    list_filter = ['is_default', 'pharmacie', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('name', 'pharmacie', 'description', 'is_default')
        }),
        ('Permissions', {
            'fields': ('permissions',),
            'classes': ('wide',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def employee_count(self, obj):
        count = obj.employees.filter(employment_status='active').count()
        return format_html('<strong>{}</strong> employé(s) actif(s)', count)
    employee_count.short_description = "Employés actifs"
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            _employee_count=Count('employees', filter=Q(employees__employment_status='active'))
        )


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = [
        'employee_id', 'nom_complet', 'pharmacie', 'role', 
        'employment_status_badge', 'salary_formatted', 'hire_date', 
        'days_employed'
    ]
    list_filter = ['employment_status', 'pharmacie', 'role', 'hire_date', ActiveEmployeeFilter]
    search_fields = [
        'employee_id', 'utilisateur__first_name', 
        'utilisateur__last_name', 'utilisateur__email'
    ]
    readonly_fields = ['employee_id', 'created_at', 'updated_at', 'days_employed']
    date_hierarchy = 'hire_date'
    list_per_page = 50
    
    inlines = [EmployeeTransferHistoryInline, WorkScheduleInline, LeaveRequestInline]
    
    fieldsets = (
        ('Informations personnelles', {
            'fields': ('utilisateur', 'employee_id', 'pharmacie', 'role')
        }),
        ('Emploi', {
            'fields': ('salary', 'hire_date', 'employment_status', 'days_employed')
        }),
        ('Contact d\'urgence', {
            'fields': ('emergency_contact_name', 'emergency_contact_phone'),
            'classes': ('collapse',)
        }),
        ('Documents et notes', {
            'fields': ('documents', 'notes'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def nom_complet(self, obj):
        return obj.get_full_name()
    nom_complet.short_description = "Nom complet"
    nom_complet.admin_order_field = 'utilisateur__last_name'
    
    def employment_status_badge(self, obj):
        colors = {
            'active': '#28a745',
            'on_leave': '#ffc107',
            'suspended': '#dc3545',
            'terminated': '#6c757d'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(obj.employment_status, '#6c757d'),
            obj.get_employment_status_display()
        )
    employment_status_badge.short_description = "Statut"
    
    def salary_formatted(self, obj):
        return format_html('<strong>{:,.0f} XAF</strong>', obj.salary)
    salary_formatted.short_description = "Salaire"
    salary_formatted.admin_order_field = 'salary'
    
    def days_employed(self, obj):
        days = (timezone.now().date() - obj.hire_date).days
        years = days // 365
        months = (days % 365) // 30
        if years > 0:
            return f"{years} an(s) {months} mois"
        return f"{months} mois"
    days_employed.short_description = "Ancienneté"
    
    actions = ['mark_as_active', 'mark_as_on_leave', 'export_selected_employees']
    
    def mark_as_active(self, request, queryset):
        updated = queryset.update(employment_status='active')
        self.message_user(request, f'{updated} employé(s) marqué(s) comme actif(s).')
    mark_as_active.short_description = "✓ Marquer comme actif"
    
    def mark_as_on_leave(self, request, queryset):
        updated = queryset.update(employment_status='on_leave')
        self.message_user(request, f'{updated} employé(s) marqué(s) en congé.')
    mark_as_on_leave.short_description = "⏸ Marquer en congé"
    
    def export_selected_employees(self, request, queryset):
        # TODO: Implémenter l'export Excel/CSV
        self.message_user(request, "Export en cours de développement...")
    export_selected_employees.short_description = "📥 Exporter la sélection"


@admin.register(EmployeeTransferHistory)
class EmployeeTransferHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'employee', 'from_pharmacie', 'arrow', 'to_pharmacie', 
        'transfer_date', 'salary_change', 'transferred_by'
    ]
    list_filter = ['transfer_date', 'from_pharmacie', 'to_pharmacie']
    search_fields = [
        'employee__employee_id', 'employee__utilisateur__last_name', 
        'reason', 'transferred_by__username'
    ]
    readonly_fields = ['transfer_date']
    date_hierarchy = 'transfer_date'
    
    fieldsets = (
        ('Transfert', {
            'fields': ('employee', 'from_pharmacie', 'to_pharmacie', 'transfer_date')
        }),
        ('Détails financiers', {
            'fields': ('old_salary', 'new_salary')
        }),
        ('Informations complémentaires', {
            'fields': ('reason', 'transferred_by', 'notes')
        }),
    )
    
    def arrow(self, obj):
        return "→"
    arrow.short_description = ""
    
    def salary_change(self, obj):
        diff = obj.new_salary - obj.old_salary
        if diff > 0:
            color = 'green'
            symbol = '+'
        elif diff < 0:
            color = 'red'
            symbol = ''
        else:
            color = 'gray'
            symbol = ''
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}{:,.0f} XAF</span>',
            color, symbol, diff
        )
    salary_change.short_description = "Δ Salaire"


# ============================================================================
# ADMIN - CLIENTS
# ============================================================================

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = [
        'client_number', 'nom_complet', 'pharmacie', 
        'loyalty_points_badge', 'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'pharmacie', 'created_at']
    search_fields = [
        'client_number', 'utilisateur__first_name', 
        'utilisateur__last_name', 'utilisateur__email'
    ]
    readonly_fields = ['client_number', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('utilisateur', 'client_number', 'pharmacie', 'is_active')
        }),
        ('Fidélité et paiement', {
            'fields': ('loyalty_points', 'preferred_payment_method')
        }),
        ('Informations médicales', {
            'fields': ('medical_notes', 'allergies'),
            'classes': ('collapse',),
            'description': 'Informations confidentielles'
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def nom_complet(self, obj):
        return obj.utilisateur.get_full_name()
    nom_complet.short_description = "Nom complet"
    nom_complet.admin_order_field = 'utilisateur__last_name'
    
    def loyalty_points_badge(self, obj):
        if obj.loyalty_points >= 1000:
            color = '#28a745'
            level = '⭐ VIP'
        elif obj.loyalty_points >= 500:
            color = '#ffc107'
            level = '🥈 Gold'
        else:
            color = '#6c757d'
            level = '🥉 Standard'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} pts</span> <small>({})</small>',
            color, obj.loyalty_points, level
        )
    loyalty_points_badge.short_description = "Points de fidélité"
    
    actions = ['activate_clients', 'deactivate_clients', 'reset_loyalty_points']
    
    def activate_clients(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} client(s) activé(s).')
    activate_clients.short_description = "✓ Activer les clients"
    
    def deactivate_clients(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} client(s) désactivé(s).')
    deactivate_clients.short_description = "✗ Désactiver les clients"
    
    def reset_loyalty_points(self, request, queryset):
        updated = queryset.update(loyalty_points=0)
        self.message_user(request, f'Points de fidélité réinitialisés pour {updated} client(s).')
    reset_loyalty_points.short_description = "🔄 Réinitialiser les points"


@admin.register(ClientTransferHistory)
class ClientTransferHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'client', 'from_pharmacie', 'to_pharmacie', 
        'transfer_date', 'loyalty_points_transferred'
    ]
    list_filter = ['transfer_date', 'from_pharmacie', 'to_pharmacie']
    search_fields = ['client__client_number', 'client__utilisateur__last_name']
    readonly_fields = ['transfer_date']
    date_hierarchy = 'transfer_date'


# ============================================================================
# ADMIN - PLANNING
# ============================================================================

@admin.register(WorkSchedule)
class WorkScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'employee', 'date', 'shift_type', 'horaire', 
        'is_recurring_badge', 'created_by'
    ]
    list_filter = ['shift_type', 'date', 'is_recurring']
    search_fields = ['employee__employee_id', 'employee__utilisateur__last_name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date'
    list_per_page = 100
    
    fieldsets = (
        ('Employé et date', {
            'fields': ('employee', 'date', 'shift_type')
        }),
        ('Horaires', {
            'fields': ('start_time', 'end_time')
        }),
        ('Récurrence', {
            'fields': ('is_recurring', 'recurrence_rule'),
            'classes': ('collapse',)
        }),
        ('Informations supplémentaires', {
            'fields': ('notes', 'created_by'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def horaire(self, obj):
        return format_html(
            '<strong>{}h{:02d}</strong> - <strong>{}h{:02d}</strong>',
            obj.start_time.hour, obj.start_time.minute,
            obj.end_time.hour, obj.end_time.minute
        )
    horaire.short_description = "Horaire"
    
    def is_recurring_badge(self, obj):
        if obj.is_recurring:
            return format_html('<span style="color: green;">✓ Récurrent</span>')
        return format_html('<span style="color: gray;">✗ Ponctuel</span>')
    is_recurring_badge.short_description = "Type"
    
    actions = ['duplicate_schedule']
    
    def duplicate_schedule(self, request, queryset):
        count = 0
        for schedule in queryset:
            schedule.pk = None
            schedule.date = schedule.date + timedelta(days=1)
            schedule.save()
            count += 1
        self.message_user(request, f'{count} planning(s) dupliqué(s) pour le lendemain.')
    duplicate_schedule.short_description = "📋 Dupliquer pour le lendemain"


# ============================================================================
# ADMIN - CONGÉS ET ABSENCES
# ============================================================================

@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = [
        'employee', 'leave_type_badge', 'periode', 'total_days', 
        'status_badge', 'reviewed_by', 'created_at'
    ]
    list_filter = ['status', 'leave_type', 'start_date', DateRangeFilter]
    search_fields = [
        'employee__employee_id', 'employee__utilisateur__last_name', 
        'reason', 'reviewed_by__username'
    ]
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Demande', {
            'fields': ('employee', 'leave_type', 'start_date', 'end_date', 'total_days', 'reason')
        }),
        ('Documents justificatifs', {
            'fields': ('supporting_documents',),
            'classes': ('collapse',)
        }),
        ('Révision', {
            'fields': ('status', 'reviewed_by', 'reviewed_at', 'review_notes', 'replacement_arranged')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def periode(self, obj):
        return format_html(
            '{} <small>au</small> {}',
            obj.start_date.strftime('%d/%m/%Y'),
            obj.end_date.strftime('%d/%m/%Y')
        )
    periode.short_description = "Période"
    
    def leave_type_badge(self, obj):
        colors = {
            'annual': '#007bff',
            'sick': '#dc3545',
            'maternity': '#e83e8c',
            'paternity': '#17a2b8',
            'emergency': '#fd7e14',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.leave_type, '#6c757d'),
            obj.get_leave_type_display()
        )
    leave_type_badge.short_description = "Type"
    
    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'approved': '#28a745',
            'rejected': '#dc3545',
            'cancelled': '#6c757d'
        }
        icons = {
            'pending': '⏳',
            'approved': '✓',
            'rejected': '✗',
            'cancelled': '⊘'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            colors.get(obj.status, 'black'),
            icons.get(obj.status, ''),
            obj.get_status_display()
        )
    status_badge.short_description = "Statut"
    
    actions = ['approve_requests', 'reject_requests']
    
    def approve_requests(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='approved',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'{updated} demande(s) approuvée(s).', 'success')
    approve_requests.short_description = "✓ Approuver les demandes"
    
    def reject_requests(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='rejected',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'{updated} demande(s) rejetée(s).', 'warning')
    reject_requests.short_description = "✗ Rejeter les demandes"


@admin.register(AbsenceRecord)
class AbsenceRecordAdmin(admin.ModelAdmin):
    list_display = [
        'employee', 'date', 'absence_type_badge', 
        'duration_display', 'is_justified_badge', 'reported_by'
    ]
    list_filter = ['absence_type', 'is_justified', 'date']
    search_fields = [
        'employee__employee_id', 'employee__utilisateur__last_name', 
        'reason', 'justification'
    ]
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Absence', {
            'fields': ('employee', 'date', 'absence_type')
        }),
        ('Horaires', {
            'fields': ('scheduled_start', 'actual_start', 'scheduled_end', 'actual_end', 'duration_minutes')
        }),
        ('Justification', {
            'fields': ('is_justified', 'reason', 'justification', 'justification_documents')
        }),
        ('Suivi', {
            'fields': ('reported_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def absence_type_badge(self, obj):
        colors = {
            'authorized': '#28a745',
            'unauthorized': '#dc3545',
            'late': '#ffc107',
            'early_departure': '#17a2b8'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.absence_type, 'black'),
            obj.get_absence_type_display()
        )
    absence_type_badge.short_description = "Type"
    
    def duration_display(self, obj):
        if obj.duration_minutes < 60:
            return f"{obj.duration_minutes} min"
        hours = obj.duration_minutes // 60
        minutes = obj.duration_minutes % 60
        return f"{hours}h{minutes:02d}"
    duration_display.short_description = "Durée"
    
    def is_justified_badge(self, obj):
        if obj.is_justified:
            return format_html('<span style="color: green;">✓ Justifié</span>')
        return format_html('<span style="color: red;">✗ Non justifié</span>')
    is_justified_badge.short_description = "Justification"


@admin.register(ReplacementRequest)
class ReplacementRequestAdmin(admin.ModelAdmin):
    list_display = [
        'requesting_employee', 'replacement_employee', 
        'date', 'horaire', 'status_badge', 'approved_by'
    ]
    list_filter = ['status', 'date']
    search_fields = [
        'requesting_employee__employee_id', 
        'replacement_employee__employee_id'
    ]
    readonly_fields = ['created_at', 'updated_at', 'approved_at']
    date_hierarchy = 'date'
    
    def horaire(self, obj):
        return f"{obj.start_time.strftime('%H:%M')} - {obj.end_time.strftime('%H:%M')}"
    horaire.short_description = "Horaire"
    
    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'approved': '#28a745',
            'rejected': '#dc3545',
            'completed': '#17a2b8',
            'cancelled': '#6c757d'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    status_badge.short_description = "Statut"


# ============================================================================
# ADMIN - SUIVI DU TEMPS
# ============================================================================

@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = [
        'employee', 'entry_type_badge', 'timestamp', 
        'method_badge', 'is_manual'
    ]
    list_filter = ['entry_type', 'method', 'is_manual', 'timestamp']
    search_fields = [
        'employee__employee_id', 'employee__utilisateur__last_name'
    ]
    readonly_fields = ['created_at']
    date_hierarchy = 'timestamp'
    list_per_page = 100
    
    def entry_type_badge(self, obj):
        icons = {
            'clock_in': '▶️',
            'clock_out': '⏹️',
            'break_start': '⏸️',
            'break_end': '▶️'
        }
        colors = {
            'clock_in': '#28a745',
            'clock_out': '#dc3545',
            'break_start': '#ffc107',
            'break_end': '#17a2b8'
        }
        return format_html(
            '<span style="color: {};">{} {}</span>',
            colors.get(obj.entry_type, 'black'),
            icons.get(obj.entry_type, ''),
            obj.get_entry_type_display()
        )
    entry_type_badge.short_description = "Type"
    
    def method_badge(self, obj):
        icons = {
            'badge': '💳',
            'qr_code': '📱',
            'biometric': '👆',
            'pin': '🔢',
            'manual': '✍️'
        }
        return format_html(
            '{} {}',
            icons.get(obj.method, ''),
            obj.get_method_display()
        )
    method_badge.short_description = "Méthode"


@admin.register(WorkSession)
class WorkSessionAdmin(admin.ModelAdmin):
    list_display = [
        'employee', 'date', 'horaire_prevu', 'actual_hours', 
        'overtime_hours', 'is_late_badge', 'is_complete'
    ]
    list_filter = ['is_late', 'is_complete', 'date']
    search_fields = [
        'employee__employee_id', 'employee__utilisateur__last_name'
    ]
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date'
    
    def horaire_prevu(self, obj):
        return format_html(
            '{}h{:02d} - {}h{:02d}',
            obj.scheduled_start.hour, obj.scheduled_start.minute,
            obj.scheduled_end.hour, obj.scheduled_end.minute
        )
    horaire_prevu.short_description = "Horaire prévu"
    
    def is_late_badge(self, obj):
        if obj.is_late:
            return format_html(
                '<span style="color: red; font-weight: bold;">⚠️ Retard ({} min)</span>',
                obj.late_duration
            )
        return format_html('<span style="color: green;">✓ À l\'heure</span>')
    is_late_badge.short_description = "Ponctualité"


# ============================================================================
# ADMIN - PERFORMANCE ET RÉMUNÉRATION
# ============================================================================

@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = [
        'employee', 'commission_type', 'amount_formatted', 
        'periode', 'is_paid_badge', 'created_by'
    ]
    list_filter = ['is_paid', 'commission_type', 'period_start']
    search_fields = [
        'employee__employee_id', 'employee__utilisateur__last_name', 
        'commission_type'
    ]
    readonly_fields = ['created_at']
    date_hierarchy = 'period_start'
    
    def periode(self, obj):
        return f"{obj.period_start.strftime('%m/%Y')} - {obj.period_end.strftime('%m/%Y')}"
    periode.short_description = "Période"
    
    def amount_formatted(self, obj):
        return format_html('<strong>{:,.0f} XAF</strong>', obj.amount)
    amount_formatted.short_description = "Montant"
    amount_formatted.admin_order_field = 'amount'
    
    def is_paid_badge(self, obj):
        if obj.is_paid:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Payée le {}</span>',
                obj.paid_date.strftime('%d/%m/%Y') if obj.paid_date else 'N/A'
            )
        return format_html('<span style="color: orange;">⏳ En attente</span>')
    is_paid_badge.short_description = "Statut paiement"
    
    actions = ['mark_as_paid']
    
    def mark_as_paid(self, request, queryset):
        updated = queryset.filter(is_paid=False).update(
            is_paid=True,
            paid_date=timezone.now().date()
        )
        self.message_user(request, f'{updated} commission(s) marquée(s) comme payée(s).')
    mark_as_paid.short_description = "💰 Marquer comme payé"


@admin.register(Bonus)
class BonusAdmin(admin.ModelAdmin):
    list_display = [
        'employee', 'bonus_type_badge', 'amount_formatted', 
        'periode', 'is_paid_badge', 'approved_by'
    ]
    list_filter = ['bonus_type', 'is_paid', 'period_start']
    search_fields = [
        'employee__employee_id', 'employee__utilisateur__last_name'
    ]
    readonly_fields = ['created_at']
    date_hierarchy = 'period_start'
    
    def periode(self, obj):
        return f"{obj.period_start.strftime('%m/%Y')} - {obj.period_end.strftime('%m/%Y')}"
    periode.short_description = "Période"
    
    def bonus_type_badge(self, obj):
        colors = {
            'performance': '#28a745',
            'holiday': '#007bff',
            'annual': '#6610f2',
            'exceptional': '#fd7e14',
            'goal': '#20c997'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.bonus_type, '#6c757d'),
            obj.get_bonus_type_display()
        )
    bonus_type_badge.short_description = "Type"
    
    def amount_formatted(self, obj):
        return format_html('<strong style="color: green;">{:,.0f} XAF</strong>', obj.amount)
    amount_formatted.short_description = "Montant"
    
    def is_paid_badge(self, obj):
        if obj.is_paid:
            return format_html('<span style="color: green;">✓ Payé</span>')
        return format_html('<span style="color: orange;">⏳ En attente</span>')
    is_paid_badge.short_description = "Paiement"


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = [
        'employee', 'evolution_role', 'evolution_salary', 
        'promotion_date', 'approved_by'
    ]
    list_filter = ['promotion_date', 'old_role', 'new_role']
    search_fields = [
        'employee__employee_id', 'employee__utilisateur__last_name'
    ]
    readonly_fields = ['created_at']
    date_hierarchy = 'promotion_date'
    
    def evolution_role(self, obj):
        return format_html(
            '{} <span style="color: gray;">→</span> <strong style="color: green;">{}</strong>',
            obj.old_role.name, obj.new_role.name
        )
    evolution_role.short_description = "Évolution de rôle"
    
    def evolution_salary(self, obj):
        diff = obj.new_salary - obj.old_salary
        percent = (diff / obj.old_salary * 100) if obj.old_salary > 0 else 0
        return format_html(
            '{:,.0f} <span style="color: gray;">→</span> <strong style="color: green;">{:,.0f}</strong> <small style="color: green;">(+{:.1f}%)</small>',
            obj.old_salary, obj.new_salary, percent
        )
    evolution_salary.short_description = "Évolution de salaire"


@admin.register(Warning)
class WarningAdmin(admin.ModelAdmin):
    list_display = [
        'employee', 'severity_badge', 'date_issued', 
        'is_acknowledged_badge', 'expiry_date', 'issued_by'
    ]
    list_filter = ['severity', 'is_acknowledged', 'date_issued']
    search_fields = [
        'employee__employee_id', 'employee__utilisateur__last_name', 
        'reason'
    ]
    readonly_fields = ['created_at', 'updated_at', 'acknowledged_at']
    date_hierarchy = 'date_issued'
    
    def severity_badge(self, obj):
        colors = {
            'verbal': '#17a2b8',
            'written': '#ffc107',
            'final': '#fd7e14',
            'suspension': '#dc3545'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(obj.severity, '#6c757d'),
            obj.get_severity_display()
        )
    severity_badge.short_description = "Sévérité"
    
    def is_acknowledged_badge(self, obj):
        if obj.is_acknowledged:
            return format_html(
                '<span style="color: green;">✓ Pris en compte le {}</span>',
                obj.acknowledged_at.strftime('%d/%m/%Y') if obj.acknowledged_at else 'N/A'
            )
        return format_html('<span style="color: orange;">⏳ En attente</span>')
    is_acknowledged_badge.short_description = "Reconnaissance"


@admin.register(Training)
class TrainingAdmin(admin.ModelAdmin):
    list_display = [
        'employee', 'title', 'provider', 'periode', 
        'status_badge', 'certificate_badge', 'score'
    ]
    list_filter = ['status', 'certificate_obtained', 'start_date']
    search_fields = [
        'employee__employee_id', 'employee__utilisateur__last_name', 
        'title', 'provider'
    ]
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'start_date'
    
    def periode(self, obj):
        return f"{obj.start_date.strftime('%d/%m/%Y')} - {obj.end_date.strftime('%d/%m/%Y')}"
    periode.short_description = "Période"
    
    def status_badge(self, obj):
        colors = {
            'scheduled': '#6c757d',
            'in_progress': '#007bff',
            'completed': '#28a745',
            'cancelled': '#dc3545'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    status_badge.short_description = "Statut"
    
    def certificate_badge(self, obj):
        if obj.certificate_obtained:
            return format_html('<span style="color: green;">✓ Obtenu</span>')
        return format_html('<span style="color: gray;">✗ Non obtenu</span>')
    certificate_badge.short_description = "Certificat"


@admin.register(PerformanceReview)
class PerformanceReviewAdmin(admin.ModelAdmin):
    list_display = [
        'employee', 'review_date', 'overall_rating_stars', 
        'reviewer', 'next_review_date'
    ]
    list_filter = ['review_date', 'reviewer']
    search_fields = [
        'employee__employee_id', 'employee__utilisateur__last_name'
    ]
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'review_date'
    
    def overall_rating_stars(self, obj):
        stars = '⭐' * int(obj.overall_rating)
        return format_html(
            '<span style="font-size: 16px;">{}</span> <strong>{:.2f}/5</strong>',
            stars, obj.overall_rating
        )
    overall_rating_stars.short_description = "Note globale"


@admin.register(PerformanceMetrics)
class PerformanceMetricsAdmin(admin.ModelAdmin):
    list_display = [
        'employee', 'periode', 'attendance_rate_bar', 
        'punctuality_rate_bar', 'total_sales_formatted'
    ]
    list_filter = ['period_start', 'period_end']
    search_fields = [
        'employee__employee_id', 'employee__utilisateur__last_name'
    ]
    readonly_fields = ['calculated_at']
    date_hierarchy = 'period_end'
    
    def periode(self, obj):
        return f"{obj.period_start.strftime('%m/%Y')} - {obj.period_end.strftime('%m/%Y')}"
    periode.short_description = "Période"
    
    def attendance_rate_bar(self, obj):
        color = '#28a745' if obj.attendance_rate >= 90 else '#ffc107' if obj.attendance_rate >= 80 else '#dc3545'
        return format_html(
            '<div style="width: 100px; background-color: #e9ecef; border-radius: 3px; overflow: hidden;">'
            '<div style="width: {}%; background-color: {}; height: 20px; text-align: center; color: white; font-weight: bold; font-size: 11px; line-height: 20px;">'
            '{:.1f}%'
            '</div></div>',
            obj.attendance_rate, color, obj.attendance_rate
        )
    attendance_rate_bar.short_description = "Présence"
    
    def punctuality_rate_bar(self, obj):
        color = '#28a745' if obj.punctuality_rate >= 90 else '#ffc107' if obj.punctuality_rate >= 80 else '#dc3545'
        return format_html(
            '<div style="width: 100px; background-color: #e9ecef; border-radius: 3px; overflow: hidden;">'
            '<div style="width: {}%; background-color: {}; height: 20px; text-align: center; color: white; font-weight: bold; font-size: 11px; line-height: 20px;">'
            '{:.1f}%'
            '</div></div>',
            obj.punctuality_rate, color, obj.punctuality_rate
        )
    punctuality_rate_bar.short_description = "Ponctualité"
    
    def total_sales_formatted(self, obj):
        return format_html('<strong>{:,.0f} XAF</strong>', obj.total_sales)
    total_sales_formatted.short_description = "Ventes totales"



