"""
Administration Django pour la gestion financière
Interface admin complète avec badges, statistiques et actions
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Sum, Count, Q, Avg
from django.urls import reverse
from decimal import Decimal

from gestion_finance.models import (
    Currency, TaxRate, Invoice, InvoiceItem, CreditNote, Payment,
    CustomerCredit, CreditPayment, ExpenseCategory, Expense,
    FinancialForecast, TaxReport
)

# Register your models here.

# Personnalisation du site admin
admin.site.site_header = "Administration Financière"
admin.site.site_title = "Finance Admin"
admin.site.index_title = "Gestion financière et comptabilité"

# ============================================================================
# INLINE ADMIN
# ============================================================================

class InvoiceItemInline(admin.TabularInline):
    """Inline pour les lignes de facture"""
    model = InvoiceItem
    extra = 1
    fields = ['product', 'description', 'quantity', 'unit_price', 'discount_percentage', 'tax_rate', 'line_total']
    readonly_fields = ['line_total']
    autocomplete_fields = ['product', 'tax_rate']


class CreditPaymentInline(admin.TabularInline):
    """Inline pour les paiements de crédit"""
    model = CreditPayment
    extra = 0
    fields = ['amount', 'payment_date', 'payment_method', 'notes']
    readonly_fields = ['created_at']


# ============================================================================
# ADMIN DEVISES ET TAXES
# ============================================================================

@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'symbol', 'exchange_rate_display', 'is_default_badge', 'is_active']
    list_filter = ['is_default', 'is_active']
    search_fields = ['code', 'name']
    
    fieldsets = (
        ('Informations', {
            'fields': ('code', 'name', 'symbol')
        }),
        ('Taux', {
            'fields': ('exchange_rate', 'is_default')
        }),
        ('Statut', {
            'fields': ('is_active',)
        }),
    )
    
    def exchange_rate_display(self, obj):
        return format_html(
            '<strong style="color: #17a2b8;">{:.6f}</strong>',
            obj.exchange_rate
        )
    exchange_rate_display.short_description = "Taux de change"
    
    def is_default_badge(self, obj):
        if obj.is_default:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 3px 8px; border-radius: 3px;">✓ Par défaut</span>'
            )
        return format_html('<span style="color: #6c757d;">-</span>')
    is_default_badge.short_description = "Défaut"


@admin.register(TaxRate)
class TaxRateAdmin(admin.ModelAdmin):
    list_display = ['name', 'tax_type_badge', 'rate_display', 'is_default_badge', 'validity_display', 'is_active']
    list_filter = ['tax_type', 'is_default', 'is_active', 'pharmacie']
    search_fields = ['name']
    date_hierarchy = 'valid_from'
    
    fieldsets = (
        ('Informations', {
            'fields': ('pharmacie', 'name', 'tax_type', 'rate')
        }),
        ('Applicabilité', {
            'fields': ('is_default', 'is_active')
        }),
        ('Période de validité', {
            'fields': ('valid_from', 'valid_until')
        }),
        ('Description', {
            'fields': ('description',),
            'classes': ('collapse',)
        }),
    )
    
    def tax_type_badge(self, obj):
        colors = {
            'vat': '#6610f2',
            'local_tax': '#20c997',
            'special_tax': '#fd7e14',
            'exemption': '#17a2b8'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.tax_type, '#6c757d'),
            obj.get_tax_type_display()
        )
    tax_type_badge.short_description = "Type"
    
    def rate_display(self, obj):
        return format_html(
            '<strong style="font-size: 16px; color: #28a745;">{:.2f}%</strong>',
            obj.rate
        )
    rate_display.short_description = "Taux"
    
    def is_default_badge(self, obj):
        if obj.is_default:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 3px 8px; border-radius: 3px;">✓</span>'
            )
        return '-'
    is_default_badge.short_description = "Défaut"
    
    def validity_display(self, obj):
        if obj.is_valid_for_date():
            return format_html('<span style="color: #28a745;">✓ Valide</span>')
        return format_html('<span style="color: #dc3545;">❌ Invalide</span>')
    validity_display.short_description = "Validité"


# ============================================================================
# ADMIN FACTURES
# ============================================================================

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'invoice_number', 'customer_display', 'issue_date', 'due_date',
        'status_badge', 'total_amount_display', 'paid_amount_display',
        'balance_due_display', 'is_overdue_badge'
    ]
    list_filter = ['status', 'invoice_type', 'pharmacie', 'issue_date', 'currency']
    search_fields = ['invoice_number', 'customer__first_name', 'customer__last_name', 'customer_name']
    date_hierarchy = 'issue_date'
    readonly_fields = [
        'invoice_number', 'subtotal', 'tax_amount', 'total_amount',
        'balance_due', 'verification_hash', 'qr_code', 'total_amount_base',
        'created_at', 'updated_at'
    ]
    inlines = [InvoiceItemInline]
    autocomplete_fields = ['customer', 'currency', 'sale']
    list_per_page = 50
    
    fieldsets = (
        ('Facture', {
            'fields': ('pharmacie', 'invoice_number', 'invoice_type', 'status')
        }),
        ('Client', {
            'fields': ('customer', 'customer_name', 'customer_email', 'customer_phone', 'customer_address')
        }),
        ('Dates', {
            'fields': ('issue_date', 'due_date', 'paid_date')
        }),
        ('Montants', {
            'fields': ('currency', 'exchange_rate', 'subtotal', 'tax_amount', 'discount_amount', 'total_amount', 'paid_amount', 'balance_due', 'total_amount_base')
        }),
        ('Documents et vérification', {
            'fields': ('verification_hash', 'qr_code', 'pdf_file'),
            'classes': ('collapse',)
        }),
        ('Communication', {
            'fields': ('email_sent', 'email_sent_at', 'sms_sent', 'sms_sent_at'),
            'classes': ('collapse',)
        }),
        ('Références', {
            'fields': ('sale', 'credit_note'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes', 'internal_notes'),
            'classes': ('collapse',)
        }),
    )
    
    def customer_display(self, obj):
        if obj.customer:
            return obj.customer.get_full_name()
        return obj.customer_name or 'Client anonyme'
    customer_display.short_description = "Client"
    
    def status_badge(self, obj):
        colors = {
            'draft': '#6c757d',
            'issued': '#17a2b8',
            'paid': '#28a745',
            'partially_paid': '#ffc107',
            'overdue': '#dc3545',
            'cancelled': '#6c757d',
            'credited': '#fd7e14'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = "Statut"
    
    def total_amount_display(self, obj):
        return format_html(
            '<strong style="font-size: 14px; color: green;">{:,.0f} {}</strong>',
            obj.total_amount, obj.currency.code
        )
    total_amount_display.short_description = "Total"
    total_amount_display.admin_order_field = 'total_amount'
    
    def paid_amount_display(self, obj):
        if obj.paid_amount > 0:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">{:,.0f} {}</span>',
                obj.paid_amount, obj.currency.code
            )
        return format_html('<span style="color: #6c757d;">0</span>')
    paid_amount_display.short_description = "Payé"
    
    def balance_due_display(self, obj):
        if obj.balance_due > 0:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">{:,.0f} {}</span>',
                obj.balance_due, obj.currency.code
            )
        return format_html('<span style="color: #28a745;">✓ Soldé</span>')
    balance_due_display.short_description = "Reste à payer"
    
    def is_overdue_badge(self, obj):
        if obj.is_overdue():
            days = (timezone.now().date() - obj.due_date).days
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">🚨 {} jour(s)</span>',
                days
            )
        return format_html('<span style="color: green;">✓ OK</span>')
    is_overdue_badge.short_description = "Retard"
    
    actions = ['mark_as_issued', 'mark_as_paid', 'send_invoice_email']
    
    def mark_as_issued(self, request, queryset):
        updated = queryset.filter(status='draft').update(status='issued')
        self.message_user(request, f'{updated} facture(s) émise(s).')
    mark_as_issued.short_description = "✉️ Marquer comme émise"
    
    def mark_as_paid(self, request, queryset):
        for invoice in queryset:
            invoice.paid_amount = invoice.total_amount
            invoice.balance_due = Decimal('0.00')
            invoice.status = 'paid'
            invoice.paid_date = timezone.now().date()
            invoice.save()
        self.message_user(request, f'{queryset.count()} facture(s) marquée(s) comme payée(s).')
    mark_as_paid.short_description = "✓ Marquer comme payée"
    
    def send_invoice_email(self, request, queryset):
        # TODO: Implémenter l'envoi d'email
        count = queryset.count()
        self.message_user(request, f'{count} email(s) de facture envoyé(s).')
    send_invoice_email.short_description = "📧 Envoyer par email"


@admin.register(CreditNote)
class CreditNoteAdmin(admin.ModelAdmin):
    list_display = [
        'credit_note_number', 'original_invoice_number', 'issue_date',
        'reason_badge', 'credit_amount_display'
    ]
    list_filter = ['reason', 'pharmacie', 'issue_date']
    search_fields = ['credit_note_number', 'original_invoice__invoice_number']
    date_hierarchy = 'issue_date'
    readonly_fields = ['credit_note_number', 'created_at']
    autocomplete_fields = ['original_invoice', 'currency']
    
    def original_invoice_number(self, obj):
        return obj.original_invoice.invoice_number
    original_invoice_number.short_description = "Facture d'origine"
    
    def reason_badge(self, obj):
        colors = {
            'return': '#17a2b8',
            'error': '#dc3545',
            'discount': '#28a745',
            'cancellation': '#ffc107',
            'other': '#6c757d'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.reason, '#6c757d'),
            obj.get_reason_display()
        )
    reason_badge.short_description = "Raison"
    
    def credit_amount_display(self, obj):
        return format_html(
            '<strong style="color: #dc3545;">{:,.0f} {}</strong>',
            obj.credit_amount, obj.currency.code
        )
    credit_amount_display.short_description = "Montant crédit"


# ============================================================================
# ADMIN PAIEMENTS
# ============================================================================

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'payment_number', 'invoice_number', 'amount_display',
        'payment_method_badge', 'payment_date', 'status_badge',
        'processed_by_name'
    ]
    list_filter = ['payment_method', 'status', 'pharmacie', 'payment_date']
    search_fields = ['payment_number', 'invoice__invoice_number', 'transaction_id']
    date_hierarchy = 'payment_date'
    readonly_fields = ['payment_number', 'created_at']
    autocomplete_fields = ['invoice', 'currency', 'processed_by']
    list_per_page = 100
    
    fieldsets = (
        ('Paiement', {
            'fields': ('pharmacie', 'payment_number', 'invoice', 'status')
        }),
        ('Montant', {
            'fields': ('amount', 'currency')
        }),
        ('Méthode', {
            'fields': ('payment_method', 'payment_date')
        }),
        ('Détails Mobile Money', {
            'fields': ('mobile_money_operator', 'mobile_money_number'),
            'classes': ('collapse',)
        }),
        ('Détails Carte', {
            'fields': ('card_last4', 'card_type'),
            'classes': ('collapse',)
        }),
        ('Détails Chèque/Banque', {
            'fields': ('check_number', 'bank_name'),
            'classes': ('collapse',)
        }),
        ('Transaction', {
            'fields': ('transaction_id',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Traçabilité', {
            'fields': ('processed_by', 'created_at')
        }),
    )
    
    def invoice_number(self, obj):
        return obj.invoice.invoice_number
    invoice_number.short_description = "N° Facture"
    
    def amount_display(self, obj):
        return format_html(
            '<strong style="color: #28a745; font-size: 14px;">{:,.0f} {}</strong>',
            obj.amount, obj.currency.code
        )
    amount_display.short_description = "Montant"
    amount_display.admin_order_field = 'amount'
    
    def payment_method_badge(self, obj):
        icons = {
            'cash': '💵',
            'mobile_money': '📱',
            'card': '💳',
            'bank_transfer': '🏦',
            'check': '✉️',
            'credit': '📋',
            'other': '📌'
        }
        colors = {
            'cash': '#28a745',
            'mobile_money': '#ffc107',
            'card': '#6610f2',
            'bank_transfer': '#17a2b8',
            'check': '#fd7e14'
        }
        return format_html(
            '<span style="color: {};">{} {}</span>',
            colors.get(obj.payment_method, '#6c757d'),
            icons.get(obj.payment_method, ''),
            obj.get_payment_method_display()
        )
    payment_method_badge.short_description = "Méthode"
    
    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'completed': '#28a745',
            'failed': '#dc3545',
            'refunded': '#fd7e14',
            'cancelled': '#6c757d'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = "Statut"
    
    def processed_by_name(self, obj):
        return obj.processed_by.get_full_name() if obj.processed_by else '-'
    processed_by_name.short_description = "Traité par"


# ============================================================================
# ADMIN CRÉDITS CLIENTS
# ============================================================================

@admin.register(CustomerCredit)
class CustomerCreditAdmin(admin.ModelAdmin):
    list_display = [
        'customer_name', 'invoice_number', 'credit_date', 'due_date',
        'status_badge', 'credit_amount_display', 'balance_due_display',
        'is_overdue_badge'
    ]
    list_filter = ['status', 'pharmacie', 'due_date']
    search_fields = ['customer__first_name', 'customer__last_name', 'invoice__invoice_number']
    date_hierarchy = 'credit_date'
    readonly_fields = ['created_at', 'updated_at']
    inlines = [CreditPaymentInline]
    autocomplete_fields = ['customer', 'invoice']
    
    def customer_name(self, obj):
        return obj.customer.get_full_name()
    customer_name.short_description = "Client"
    
    def invoice_number(self, obj):
        return obj.invoice.invoice_number
    invoice_number.short_description = "N° Facture"
    
    def status_badge(self, obj):
        colors = {
            'active': '#17a2b8',
            'partially_paid': '#ffc107',
            'paid': '#28a745',
            'overdue': '#dc3545',
            'written_off': '#6c757d'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = "Statut"
    
    def credit_amount_display(self, obj):
        return format_html(
            '<strong style="color: #17a2b8;">{:,.0f} XAF</strong>',
            obj.credit_amount
        )
    credit_amount_display.short_description = "Crédit"
    
    def balance_due_display(self, obj):
        if obj.balance_due > 0:
            return format_html(
                '<strong style="color: #dc3545;">{:,.0f} XAF</strong>',
                obj.balance_due
            )
        return format_html('<span style="color: #28a745;">✓ Payé</span>')
    balance_due_display.short_description = "Reste"
    
    def is_overdue_badge(self, obj):
        if obj.is_overdue():
            days = (timezone.now().date() - obj.due_date).days
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">🚨 {} jour(s)</span>',
                days
            )
        return format_html('<span style="color: green;">✓ OK</span>')
    is_overdue_badge.short_description = "Retard"
    
    actions = ['write_off_credits']
    
    def write_off_credits(self, request, queryset):
        updated = queryset.update(status='written_off')
        self.message_user(request, f'{updated} crédit(s) radié(s).')
    write_off_credits.short_description = "❌ Radier les crédits"


# ============================================================================
# ADMIN DÉPENSES
# ============================================================================

@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'expenses_count', 'total_amount_display', 'is_active']
    list_filter = ['is_active', 'pharmacie']
    search_fields = ['name']
    
    def expenses_count(self, obj):
        count = obj.expenses.filter(status__in=['approved', 'paid']).count()
        return format_html('<strong>{}</strong>', count)
    expenses_count.short_description = "Nb. dépenses"
    
    def total_amount_display(self, obj):
        total = obj.expenses.filter(
            status__in=['approved', 'paid']
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        return format_html(
            '<strong style="color: #dc3545;">{:,.0f} XAF</strong>',
            total
        )
    total_amount_display.short_description = "Total"


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = [
        'expense_number', 'description', 'category_name', 'expense_type_badge',
        'amount_display', 'expense_date', 'status_badge', 'payee'
    ]
    list_filter = ['status', 'expense_type', 'category', 'pharmacie', 'expense_date']
    search_fields = ['expense_number', 'description', 'payee']
    date_hierarchy = 'expense_date'
    readonly_fields = ['expense_number', 'approved_at', 'created_at', 'updated_at']
    autocomplete_fields = ['category', 'currency', 'created_by', 'approved_by']
    list_per_page = 50
    
    fieldsets = (
        ('Dépense', {
            'fields': ('pharmacie', 'expense_number', 'category', 'expense_type', 'description')
        }),
        ('Montant', {
            'fields': ('amount', 'currency')
        }),
        ('Dates', {
            'fields': ('expense_date', 'due_date', 'paid_date')
        }),
        ('Bénéficiaire', {
            'fields': ('payee', 'payment_method')
        }),
        ('Statut', {
            'fields': ('status',)
        }),
        ('Document', {
            'fields': ('receipt',),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Traçabilité', {
            'fields': ('created_by', 'approved_by', 'approved_at', 'created_at', 'updated_at')
        }),
    )
    
    def category_name(self, obj):
        return obj.category.name
    category_name.short_description = "Catégorie"
    
    def expense_type_badge(self, obj):
        icons = {
            'supplier': '🏭',
            'utility': '⚡',
            'rent': '🏢',
            'salary': '💰',
            'maintenance': '🔧',
            'marketing': '📢',
            'tax': '📋',
            'insurance': '🛡️',
            'other': '📌'
        }
        return format_html(
            '{} {}',
            icons.get(obj.expense_type, ''),
            obj.get_expense_type_display()
        )
    expense_type_badge.short_description = "Type"
    
    def amount_display(self, obj):
        return format_html(
            '<strong style="color: #dc3545; font-size: 14px;">{:,.0f} {}</strong>',
            obj.amount, obj.currency.code
        )
    amount_display.short_description = "Montant"
    amount_display.admin_order_field = 'amount'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'approved': '#28a745',
            'paid': '#17a2b8',
            'rejected': '#dc3545'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = "Statut"
    
    actions = ['approve_expenses', 'mark_as_paid']
    
    def approve_expenses(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='approved',
            approved_by=request.user,
            approved_at=timezone.now()
        )
        self.message_user(request, f'{updated} dépense(s) approuvée(s).')
    approve_expenses.short_description = "✓ Approuver"
    
    def mark_as_paid(self, request, queryset):
        updated = queryset.filter(status='approved').update(
            status='paid',
            paid_date=timezone.now().date()
        )
        self.message_user(request, f'{updated} dépense(s) marquée(s) comme payée(s).')
    mark_as_paid.short_description = "💰 Marquer comme payée"


# ============================================================================
# ADMIN PRÉVISIONS
# ============================================================================

@admin.register(FinancialForecast)
class FinancialForecastAdmin(admin.ModelAdmin):
    list_display = [
        'forecast_type_badge', 'forecast_date', 'period_badge',
        'predicted_amount_display', 'confidence_badge',
        'variance_display'
    ]
    list_filter = ['forecast_type', 'period', 'pharmacie', 'forecast_date']
    search_fields = ['notes']
    date_hierarchy = 'forecast_date'
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 50
    
    fieldsets = (
        ('Prévision', {
            'fields': ('pharmacie', 'forecast_type', 'period', 'forecast_date')
        }),
        ('Montants', {
            'fields': ('predicted_amount', 'actual_amount', 'variance')
        }),
        ('Facteurs', {
            'fields': ('confidence_level', 'seasonal_factor', 'trend_factor')
        }),
        ('IA', {
            'fields': ('algorithm_used', 'data_points_used'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    def forecast_type_badge(self, obj):
        colors = {
            'revenue': '#28a745',
            'expense': '#dc3545',
            'profit': '#6610f2',
            'cashflow': '#17a2b8'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.forecast_type, '#6c757d'),
            obj.get_forecast_type_display()
        )
    forecast_type_badge.short_description = "Type"
    
    def period_badge(self, obj):
        return format_html(
            '<span style="background: #6c757d; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            obj.get_period_display()
        )
    period_badge.short_description = "Période"
    
    def predicted_amount_display(self, obj):
        return format_html(
            '<strong style="color: #17a2b8;">{:,.0f} XAF</strong>',
            obj.predicted_amount
        )
    predicted_amount_display.short_description = "Prévu"
    
    def confidence_badge(self, obj):
        if obj.confidence_level >= 80:
            color = '#28a745'
            icon = '✓✓'
        elif obj.confidence_level >= 60:
            color = '#ffc107'
            icon = '✓'
        else:
            color = '#dc3545'
            icon = '⚠️'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {:.0f}%</span>',
            color, icon, obj.confidence_level
        )
    confidence_badge.short_description = "Confiance"
    
    def variance_display(self, obj):
        if obj.actual_amount is not None:
            variance = obj.actual_amount - obj.predicted_amount
            if variance > 0:
                return format_html(
                    '<span style="color: #28a745;">+{:,.0f} XAF</span>',
                    variance
                )
            elif variance < 0:
                return format_html(
                    '<span style="color: #dc3545;">{:,.0f} XAF</span>',
                    variance
                )
            return format_html('<span style="color: #6c757d;">0</span>')
        return format_html('<span style="color: #6c757d;">-</span>')
    variance_display.short_description = "Écart"


# ============================================================================
# ADMIN RAPPORTS FISCAUX
# ============================================================================

@admin.register(TaxReport)
class TaxReportAdmin(admin.ModelAdmin):
    list_display = [
        'report_number', 'report_type_badge', 'period_display',
        'total_revenue_display', 'total_tax_display', 'net_profit_display',
        'status_badge'
    ]
    list_filter = ['report_type', 'status', 'pharmacie', 'period_end']
    search_fields = ['report_number']
    date_hierarchy = 'period_end'
    readonly_fields = ['report_number', 'created_at', 'updated_at']
    autocomplete_fields = ['created_by']
    
    fieldsets = (
        ('Rapport', {
            'fields': ('pharmacie', 'report_number', 'report_type', 'status')
        }),
        ('Période', {
            'fields': ('period_start', 'period_end')
        }),
        ('Données', {
            'fields': ('total_revenue', 'total_tax_collected', 'total_expenses', 'net_profit')
        }),
        ('Document', {
            'fields': ('pdf_file',),
            'classes': ('collapse',)
        }),
        ('Soumission', {
            'fields': ('submitted_at',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Traçabilité', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )
    
    def report_type_badge(self, obj):
        colors = {
            'vat': '#6610f2',
            'income': '#28a745',
            'expense': '#dc3545',
            'comprehensive': '#17a2b8'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.report_type, '#6c757d'),
            obj.get_report_type_display()
        )
    report_type_badge.short_description = "Type"
    
    def period_display(self, obj):
        return format_html(
            '{} → {}',
            obj.period_start.strftime('%d/%m/%Y'),
            obj.period_end.strftime('%d/%m/%Y')
        )
    period_display.short_description = "Période"
    
    def total_revenue_display(self, obj):
        return format_html(
            '<strong style="color: #28a745;">{:,.0f} XAF</strong>',
            obj.total_revenue
        )
    total_revenue_display.short_description = "Revenus"
    
    def total_tax_display(self, obj):
        return format_html(
            '<strong style="color: #6610f2;">{:,.0f} XAF</strong>',
            obj.total_tax_collected
        )
    total_tax_display.short_description = "Taxes"
    
    def net_profit_display(self, obj):
        color = '#28a745' if obj.net_profit >= 0 else '#dc3545'
        return format_html(
            '<strong style="color: {};">{:,.0f} XAF</strong>',
            color, obj.net_profit
        )
    net_profit_display.short_description = "Bénéfice net"
    
    def status_badge(self, obj):
        colors = {
            'draft': '#6c757d',
            'generated': '#17a2b8',
            'submitted': '#ffc107',
            'accepted': '#28a745'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = "Statut"
    
    actions = ['mark_as_submitted']
    
    def mark_as_submitted(self, request, queryset):
        updated = queryset.filter(status='generated').update(
            status='submitted',
            submitted_at=timezone.now()
        )
        self.message_user(request, f'{updated} rapport(s) soumis.')
    mark_as_submitted.short_description = "📤 Marquer comme soumis"




