"""
Configuration de l'interface d'administration Django
pour la gestion des ventes
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta

from gestion_vente.models import (
    ProductCategory, Product, Promotion, Coupon,
    Sale, SaleItem, Payment, PaymentInstallment,
    ElectronicPrescription, SalesAnalytics, ProductPerformance,
    CustomerPurchasePattern, ProductRecommendation,
    FraudAlert, PurchaseAnomalyLog
)

# Register your models here.


# Personnalisation du site admin
admin.site.site_header = "Administration Ventes Pharmacie"
admin.site.site_title = "Ventes Admin"
admin.site.index_title = "Gestion des ventes et produits"




# ============================================================================
# INLINE ADMIN
# ============================================================================

class SaleItemInline(admin.TabularInline):
    """Inline pour les lignes de vente"""
    model = SaleItem
    extra = 0
    fields = ['product', 'quantity', 'unit_price', 'discount_percentage', 'line_total', 'profit_amount']
    readonly_fields = ['line_total', 'profit_amount']


class PaymentInline(admin.TabularInline):
    """Inline pour les paiements"""
    model = Payment
    extra = 0
    fields = ['payment_method', 'amount', 'status', 'payment_date']
    readonly_fields = ['payment_date']


# ============================================================================
# ADMIN PRODUITS
# ============================================================================

@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'products_count', 'display_order', 'is_active']
    list_filter = ['is_active', 'parent']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('name', 'slug', 'description', 'parent')
        }),
        ('Présentation', {
            'fields': ('image', 'display_order', 'is_active')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def products_count(self, obj):
        count = obj.products.filter(is_active=True).count()
        return format_html('<strong>{}</strong> produit(s)', count)
    products_count.short_description = "Produits actifs"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'sku', 'name', 'category', 'pharmacie', 'stock_status_badge',
        'selling_price_formatted', 'margin_badge', 'is_available_online',
        'is_active'
    ]
    list_filter = [
        'is_active', 'is_available_online', 'requires_prescription',
        'category', 'pharmacie', 'is_featured'
    ]
    search_fields = ['name', 'sku', 'barcode', 'active_ingredient']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at', 'margin_display']
    date_hierarchy = 'created_at'
    list_per_page = 50
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('pharmacie', 'name', 'slug', 'category', 'sku', 'barcode', 'description')
        }),
        ('Informations médicales', {
            'fields': (
                'active_ingredient', 'dosage', 'pharmaceutical_form',
                'manufacturer', 'requires_prescription'
            ),
            'classes': ('collapse',)
        }),
        ('Prix et marges', {
            'fields': (
                'purchase_price', 'selling_price', 'tax_rate', 'margin_display'
            )
        }),
        ('Stock', {
            'fields': ('stock_quantity', 'min_stock_level')
        }),
        ('Vente en ligne', {
            'fields': ('is_available_online', 'is_featured')
        }),
        ('Instructions et sécurité', {
            'fields': (
                'usage_instructions', 'side_effects',
                'contraindications', 'storage_conditions'
            ),
            'classes': ('collapse',)
        }),
        ('Images', {
            'fields': ('main_image', 'images'),
            'classes': ('collapse',)
        }),
        ('Statut', {
            'fields': ('is_active', 'created_by')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def stock_status_badge(self, obj):
        if obj.is_out_of_stock():
            color = 'red'
            icon = '❌'
            text = 'Rupture'
        elif obj.is_low_stock():
            color = 'orange'
            icon = '⚠️'
            text = f'Faible ({obj.stock_quantity})'
        else:
            color = 'green'
            icon = '✓'
            text = f'OK ({obj.stock_quantity})'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, text
        )
    stock_status_badge.short_description = "Stock"
    
    def selling_price_formatted(self, obj):
        return format_html('<strong>{:,.0f} XAF</strong>', obj.selling_price)
    selling_price_formatted.short_description = "Prix de vente"
    selling_price_formatted.admin_order_field = 'selling_price'
    
    def margin_badge(self, obj):
        margin = obj.calculate_margin()
        percentage = margin['margin_percentage']
        
        if percentage >= 30:
            color = 'green'
        elif percentage >= 15:
            color = 'orange'
        else:
            color = 'red'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color, percentage
        )
    margin_badge.short_description = "Marge"
    
    def margin_display(self, obj):
        if obj.pk:
            margin = obj.calculate_margin()
            return format_html(
                '<strong>Montant:</strong> {:,.0f} XAF<br>'
                '<strong>Pourcentage:</strong> {:.2f}%',
                margin['margin_amount'], margin['margin_percentage']
            )
        return "-"
    margin_display.short_description = "Marge calculée"
    
    actions = ['mark_available_online', 'mark_unavailable_online', 'activate_products']
    
    def mark_available_online(self, request, queryset):
        updated = queryset.update(is_available_online=True)
        self.message_user(request, f'{updated} produit(s) disponible(s) en ligne.')
    mark_available_online.short_description = "✓ Rendre disponible en ligne"
    
    def mark_unavailable_online(self, request, queryset):
        updated = queryset.update(is_available_online=False)
        self.message_user(request, f'{updated} produit(s) retiré(s) de la vente en ligne.')
    mark_unavailable_online.short_description = "✗ Retirer de la vente en ligne"
    
    def activate_products(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} produit(s) activé(s).')
    activate_products.short_description = "✓ Activer les produits"


# ============================================================================
# ADMIN PROMOTIONS
# ============================================================================

@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'pharmacie', 'discount_badge', 'scope_badge',
        'periode', 'usage_progress', 'is_active'
    ]
    list_filter = [
        'is_active', 'discount_type', 'promotion_scope',
        'start_date', 'pharmacie'
    ]
    search_fields = ['name', 'promotion_code', 'description']
    readonly_fields = ['current_uses', 'created_at', 'updated_at']
    date_hierarchy = 'start_date'
    filter_horizontal = ['applicable_products', 'applicable_categories']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('pharmacie', 'name', 'description', 'promotion_code')
        }),
        ('Type de remise', {
            'fields': ('discount_type', 'discount_value', 'promotion_scope')
        }),
        ('Applicabilité', {
            'fields': ('applicable_products', 'applicable_categories')
        }),
        ('Conditions', {
            'fields': (
                'min_purchase_amount', 'min_quantity',
                'max_uses', 'max_uses_per_customer', 'current_uses'
            )
        }),
        ('Périodes', {
            'fields': ('start_date', 'end_date', 'happy_hours_start', 'happy_hours_end')
        }),
        ('Options', {
            'fields': ('is_active', 'is_stackable')
        }),
    )
    
    def discount_badge(self, obj):
        if obj.discount_type == 'percentage':
            return format_html(
                '<span style="background: #28a745; color: white; padding: 3px 8px; border-radius: 3px;">{:.0f}%</span>',
                obj.discount_value
            )
        else:
            return format_html(
                '<span style="background: #007bff; color: white; padding: 3px 8px; border-radius: 3px;">{:,.0f} XAF</span>',
                obj.discount_value
            )
    discount_badge.short_description = "Remise"
    
    def scope_badge(self, obj):
        colors = {
            'product': '#6610f2',
            'category': '#fd7e14',
            'all_products': '#20c997',
            'loyal_customers': '#e83e8c'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.promotion_scope, '#6c757d'),
            obj.get_promotion_scope_display()
        )
    scope_badge.short_description = "Portée"
    
    def periode(self, obj):
        return format_html(
            '{} <small>au</small> {}',
            obj.start_date.strftime('%d/%m/%Y'),
            obj.end_date.strftime('%d/%m/%Y')
        )
    periode.short_description = "Période"
    
    def usage_progress(self, obj):
        if obj.max_uses:
            percentage = (obj.current_uses / obj.max_uses) * 100
            color = 'green' if percentage < 80 else 'orange' if percentage < 100 else 'red'
            return format_html(
                '<div style="width: 100px; background: #e9ecef; border-radius: 3px; overflow: hidden;">'
                '<div style="width: {}%; background: {}; height: 20px; text-align: center; color: white; font-size: 11px; line-height: 20px;">'
                '{}/{}'
                '</div></div>',
                min(percentage, 100), color, obj.current_uses, obj.max_uses
            )
        return f"{obj.current_uses} utilisation(s)"
    usage_progress.short_description = "Utilisation"


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = [
        'code', 'pharmacie', 'discount_display', 'usage_display',
        'validity_period', 'is_active'
    ]
    list_filter = ['is_active', 'discount_type', 'pharmacie', 'valid_from']
    search_fields = ['code']
    readonly_fields = ['current_uses', 'created_at']
    
    def discount_display(self, obj):
        if obj.discount_type == 'percentage':
            return f"{obj.discount_value}%"
        return f"{obj.discount_value:,.0f} XAF"
    discount_display.short_description = "Remise"
    
    def usage_display(self, obj):
        if obj.max_uses:
            return f"{obj.current_uses}/{obj.max_uses}"
        return f"{obj.current_uses}"
    usage_display.short_description = "Utilisations"
    
    def validity_period(self, obj):
        return f"{obj.valid_from.strftime('%d/%m/%Y')} - {obj.valid_until.strftime('%d/%m/%Y')}"
    validity_period.short_description = "Validité"


# ============================================================================
# ADMIN VENTES
# ============================================================================

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = [
        'sale_number', 'sale_type', 'customer_display', 'total_amount_formatted',
        'profit_badge', 'status_badge', 'sale_date', 'payment_status'
    ]
    list_filter = ['status', 'sale_type', 'pharmacie', 'sale_date', 'is_offline_sale']
    search_fields = ['sale_number', 'customer__first_name', 'customer__last_name', 'customer_name']
    readonly_fields = [
        'sale_number', 'subtotal', 'discount_amount', 'tax_amount',
        'total_amount', 'profit_amount', 'created_at', 'updated_at'
    ]
    date_hierarchy = 'sale_date'
    inlines = [SaleItemInline, PaymentInline]
    list_per_page = 50
    
    fieldsets = (
        ('Vente', {
            'fields': ('pharmacie', 'sale_number', 'sale_type', 'status')
        }),
        ('Client', {
            'fields': ('customer', 'customer_name', 'customer_phone', 'customer_email')
        }),
        ('Montants', {
            'fields': (
                'subtotal', 'discount_amount', 'tax_amount',
                'total_amount', 'profit_amount'
            )
        }),
        ('Promotions', {
            'fields': ('applied_promotions', 'applied_coupon'),
            'classes': ('collapse',)
        }),
        ('Ordonnance', {
            'fields': ('prescription',),
            'classes': ('collapse',)
        }),
        ('Informations complémentaires', {
            'fields': ('cashier', 'notes', 'internal_notes', 'ticket_qr_code'),
            'classes': ('collapse',)
        }),
        ('Synchronisation', {
            'fields': ('is_offline_sale', 'synced_at'),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('sale_date', 'completed_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def customer_display(self, obj):
        if obj.customer:
            return obj.customer.get_full_name()
        return obj.customer_name or "Client anonyme"
    customer_display.short_description = "Client"
    
    def total_amount_formatted(self, obj):
        return format_html('<strong>{:,.0f} XAF</strong>', obj.total_amount)
    total_amount_formatted.short_description = "Montant total"
    total_amount_formatted.admin_order_field = 'total_amount'
    
    def profit_badge(self, obj):
        if obj.profit_amount > 0:
            margin_percentage = (obj.profit_amount / obj.total_amount * 100) if obj.total_amount > 0 else 0
            color = 'green' if margin_percentage >= 20 else 'orange'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{:,.0f} XAF ({:.1f}%)</span>',
                color, obj.profit_amount, margin_percentage
            )
        return format_html('<span style="color: red;">0 XAF</span>')
    profit_badge.short_description = "Bénéfice"
    
    def status_badge(self, obj):
        colors = {
            'draft': '#6c757d',
            'pending': '#ffc107',
            'confirmed': '#17a2b8',
            'processing': '#007bff',
            'completed': '#28a745',
            'cancelled': '#dc3545',
            'refunded': '#fd7e14'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = "Statut"
    
    def payment_status(self, obj):
        total_paid = obj.payments.filter(status='completed').aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        if total_paid >= obj.total_amount:
            return format_html('<span style="color: green;">✓ Payé</span>')
        elif total_paid > 0:
            return format_html(
                '<span style="color: orange;">Partiel ({:,.0f}/{:,.0f})</span>',
                total_paid, obj.total_amount
            )
        return format_html('<span style="color: red;">Non payé</span>')
    payment_status.short_description = "Paiement"
    
    actions = ['mark_as_completed', 'export_selected']
    
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='completed', completed_at=timezone.now())
        self.message_user(request, f'{updated} vente(s) marquée(s) comme terminée(s).')
    mark_as_completed.short_description = "✓ Marquer comme terminée"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'sale', 'payment_method_badge', 'amount_formatted',
        'status_badge', 'payment_date', 'is_installment'
    ]
    list_filter = ['payment_method', 'status', 'is_installment', 'payment_date']
    search_fields = ['sale__sale_number', 'transaction_id', 'reference_number']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'payment_date'
    
    def payment_method_badge(self, obj):
        icons = {
            'cash': '💵',
            'card': '💳',
            'mobile_money': '📱',
            'online': '🌐',
            'check': '✔️',
            'transfer': '🔄',
            'deferred': '⏰'
        }
        return format_html(
            '{} {}',
            icons.get(obj.payment_method, ''),
            obj.get_payment_method_display()
        )
    payment_method_badge.short_description = "Méthode"
    
    def amount_formatted(self, obj):
        return format_html('<strong>{:,.0f} XAF</strong>', obj.amount)
    amount_formatted.short_description = "Montant"
    
    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'processing': '#17a2b8',
            'completed': '#28a745',
            'failed': '#dc3545',
            'cancelled': '#6c757d',
            'refunded': '#fd7e14'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    status_badge.short_description = "Statut"


# ============================================================================
# ADMIN ORDONNANCES
# ============================================================================

@admin.register(ElectronicPrescription)
class ElectronicPrescriptionAdmin(admin.ModelAdmin):
    list_display = [
        'prescription_number', 'patient_name', 'doctor_name',
        'prescription_date', 'expiry_status', 'status_badge',
        'fraud_indicator'
    ]
    list_filter = ['status', 'is_duplicate', 'pharmacie', 'prescription_date']
    search_fields = [
        'prescription_number', 'patient__first_name', 'patient__last_name',
        'doctor_name', 'doctor_license'
    ]
    readonly_fields = [
        'prescription_number', 'is_duplicate', 'fraud_score',
        'fraud_flags', 'created_at', 'updated_at'
    ]
    date_hierarchy = 'prescription_date'
    
    fieldsets = (
        ('Ordonnance', {
            'fields': ('pharmacie', 'prescription_number', 'prescription_date', 'expiry_date')
        }),
        ('Patient', {
            'fields': ('patient',)
        }),
        ('Prescripteur', {
            'fields': ('doctor_name', 'doctor_license', 'doctor_phone')
        }),
        ('Document', {
            'fields': ('document',)
        }),
        ('Validation', {
            'fields': ('status', 'validated_by', 'validated_at', 'validation_notes')
        }),
        ('Détection de fraude', {
            'fields': ('is_duplicate', 'fraud_score', 'fraud_flags'),
            'classes': ('collapse',)
        }),
    )
    
    def patient_name(self, obj):
        return obj.patient.get_full_name()
    patient_name.short_description = "Patient"
    
    def expiry_status(self, obj):
        if obj.is_expired():
            return format_html('<span style="color: red;">❌ Expirée</span>')
        
        days_left = (obj.expiry_date - timezone.now().date()).days
        if days_left <= 3:
            return format_html('<span style="color: orange;">⚠️ {} jour(s)</span>', days_left)
        return format_html('<span style="color: green;">✓ Valide</span>')
    expiry_status.short_description = "Validité"
    
    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'validated': '#28a745',
            'rejected': '#dc3545',
            'dispensed': '#17a2b8',
            'partially_dispensed': '#fd7e14',
            'archived': '#6c757d'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = "Statut"
    
    def fraud_indicator(self, obj):
        if obj.fraud_score >= 70:
            return format_html(
                '<span style="color: red; font-weight: bold;">🚨 {} / 100</span>',
                obj.fraud_score
            )
        elif obj.fraud_score >= 40:
            return format_html(
                '<span style="color: orange; font-weight: bold;">⚠️ {} / 100</span>',
                obj.fraud_score
            )
        return format_html('<span style="color: green;">✓ {} / 100</span>', obj.fraud_score)
    fraud_indicator.short_description = "Score fraude"
    
    actions = ['validate_prescriptions', 'reject_prescriptions']
    
    def validate_prescriptions(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='validated',
            validated_by=request.user,
            validated_at=timezone.now()
        )
        self.message_user(request, f'{updated} ordonnance(s) validée(s).')
    validate_prescriptions.short_description = "✓ Valider les ordonnances"
    
    def reject_prescriptions(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='rejected',
            validated_by=request.user,
            validated_at=timezone.now()
        )
        self.message_user(request, f'{updated} ordonnance(s) rejetée(s).')
    reject_prescriptions.short_description = "✗ Rejeter les ordonnances"


# ============================================================================
# ADMIN ANALYTICS
# ============================================================================

@admin.register(SalesAnalytics)
class SalesAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'pharmacie', 'period_display', 'sales_count',
        'revenue_display', 'profit_display', 'trend_badge'
    ]
    list_filter = ['period_type', 'pharmacie', 'period_start']
    readonly_fields = ['calculated_at']
    date_hierarchy = 'period_start'
    
    def period_display(self, obj):
        return f"{obj.get_period_type_display()}: {obj.period_start} - {obj.period_end}"
    period_display.short_description = "Période"
    
    def sales_count(self, obj):
        return format_html('<strong>{}</strong> vente(s)', obj.total_sales_count)
    sales_count.short_description = "Ventes"
    
    def revenue_display(self, obj):
        return format_html('<strong style="color: green;">{:,.0f} XAF</strong>', obj.total_revenue)
    revenue_display.short_description = "CA"
    
    def profit_display(self, obj):
        margin = (obj.total_profit / obj.total_revenue * 100) if obj.total_revenue > 0 else 0
        return format_html(
            '<strong>{:,.0f} XAF</strong> <small>({:.1f}%)</small>',
            obj.total_profit, margin
        )
    profit_display.short_description = "Bénéfice"
    
    def trend_badge(self, obj):
        if obj.revenue_trend > 0:
            return format_html(
                '<span style="color: green;">📈 +{:.1f}%</span>',
                obj.revenue_trend
            )
        elif obj.revenue_trend < 0:
            return format_html(
                '<span style="color: red;">📉 {:.1f}%</span>',
                obj.revenue_trend
            )
        return format_html('<span style="color: gray;">→ 0%</span>')
    trend_badge.short_description = "Tendance"


@admin.register(ProductPerformance)
class ProductPerformanceAdmin(admin.ModelAdmin):
    list_display = [
        'product', 'period_range', 'units_sold', 'revenue_display',
        'trend_indicator', 'restock_status'
    ]
    list_filter = ['is_declining', 'restock_recommended', 'period_start']
    search_fields = ['product__name', 'product__sku']
    readonly_fields = ['calculated_at']
    
    def period_range(self, obj):
        return f"{obj.period_start} - {obj.period_end}"
    period_range.short_description = "Période"
    
    def revenue_display(self, obj):
        return format_html('{:,.0f} XAF', obj.revenue)
    revenue_display.short_description = "CA"
    
    def trend_indicator(self, obj):
        if obj.sales_trend > 10:
            return format_html('<span style="color: green;">📈 +{:.1f}%</span>', obj.sales_trend)
        elif obj.sales_trend < -10:
            return format_html('<span style="color: red;">📉 {:.1f}%</span>', obj.sales_trend)
        return format_html('<span style="color: gray;">→ {:.1f}%</span>', obj.sales_trend)
    trend_indicator.short_description = "Tendance"
    
    def restock_status(self, obj):
        if obj.restock_recommended:
            return format_html(
                '<span style="color: orange; font-weight: bold;">⚠️ {} unités</span>',
                obj.recommended_quantity
            )
        return format_html('<span style="color: green;">✓ OK</span>')
    restock_status.short_description = "Réassort"


# ============================================================================
# ADMIN FRAUDE
# ============================================================================

@admin.register(FraudAlert)
class FraudAlertAdmin(admin.ModelAdmin):
    list_display = [
        'alert_type_display', 'severity_badge', 'risk_score_badge',
        'customer', 'status_badge', 'created_at'
    ]
    list_filter = ['alert_type', 'severity', 'status', 'pharmacie', 'created_at']
    search_fields = ['customer__first_name', 'customer__last_name', 'description']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Alerte', {
            'fields': ('pharmacie', 'alert_type', 'severity', 'status')
        }),
        ('Entités concernées', {
            'fields': ('customer', 'sale', 'prescription', 'product')
        }),
        ('Détails', {
            'fields': ('description', 'indicators', 'risk_score')
        }),
        ('Investigation', {
            'fields': (
                'investigated_by', 'investigation_notes',
                'resolution_notes', 'actions_taken'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def alert_type_display(self, obj):
        icons = {
            'duplicate_prescription': '📋',
            'unusual_purchase_pattern': '🔍',
            'excessive_quantity': '📦',
            'rapid_repeat_purchase': '⏱️',
            'suspicious_prescription': '⚠️',
            'resale_indicator': '💰',
            'multiple_pharmacies': '🏪'
        }
        return format_html(
            '{} {}',
            icons.get(obj.alert_type, ''),
            obj.get_alert_type_display()
        )
    alert_type_display.short_description = "Type"
    
    def severity_badge(self, obj):
        colors = {
            'low': '#17a2b8',
            'medium': '#ffc107',
            'high': '#fd7e14',
            'critical': '#dc3545'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(obj.severity, '#6c757d'),
            obj.get_severity_display()
        )
    severity_badge.short_description = "Sévérité"
    
    def risk_score_badge(self, obj):
        if obj.risk_score >= 70:
            color = '#dc3545'
        elif obj.risk_score >= 40:
            color = '#ffc107'
        else:
            color = '#28a745'
        
        return format_html(
            '<div style="width: 60px; background: #e9ecef; border-radius: 3px; overflow: hidden;">'
            '<div style="width: {}%; background: {}; height: 20px; text-align: center; color: white; font-size: 11px; line-height: 20px; font-weight: bold;">'
            '{}'
            '</div></div>',
            obj.risk_score, color, obj.risk_score
        )
    risk_score_badge.short_description = "Score"
    
    def status_badge(self, obj):
        colors = {
            'new': '#007bff',
            'investigating': '#ffc107',
            'confirmed': '#dc3545',
            'false_positive': '#28a745',
            'resolved': '#6c757d'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    status_badge.short_description = "Statut"
    
    actions = ['mark_investigating', 'mark_resolved', 'mark_false_positive']
    
    def mark_investigating(self, request, queryset):
        updated = queryset.update(
            status='investigating',
            investigated_by=request.user
        )
        self.message_user(request, f'{updated} alerte(s) en investigation.')
    mark_investigating.short_description = "🔍 Marquer en investigation"
    
    def mark_resolved(self, request, queryset):
        updated = queryset.update(
            status='resolved',
            resolved_at=timezone.now()
        )
        self.message_user(request, f'{updated} alerte(s) résolue(s).')
    mark_resolved.short_description = "✓ Marquer comme résolu"
    
    def mark_false_positive(self, request, queryset):
        updated = queryset.update(status='false_positive')
        self.message_user(request, f'{updated} fausse(s) alerte(s).')
    mark_false_positive.short_description = "✗ Marquer fausse alerte"


@admin.register(CustomerPurchasePattern)
class CustomerPurchasePatternAdmin(admin.ModelAdmin):
    list_display = [
        'customer', 'total_purchases', 'total_spent_display',
        'average_basket_display', 'frequency_display', 'risk_badge'
    ]
    list_filter = ['is_at_risk', 'pharmacie']
    search_fields = ['customer__first_name', 'customer__last_name']
    readonly_fields = ['updated_at']
    
    def total_spent_display(self, obj):
        return format_html('{:,.0f} XAF', obj.total_spent)
    total_spent_display.short_description = "Total dépensé"
    
    def average_basket_display(self, obj):
        return format_html('{:,.0f} XAF', obj.average_basket_value)
    average_basket_display.short_description = "Panier moyen"
    
    def frequency_display(self, obj):
        if obj.average_purchase_frequency > 0:
            return f"{obj.average_purchase_frequency} jour(s)"
        return "-"
    frequency_display.short_description = "Fréquence"
    
    def risk_badge(self, obj):
        if obj.is_at_risk:
            return format_html('<span style="color: red; font-weight: bold;">⚠️ À risque</span>')
        return format_html('<span style="color: green;">✓ OK</span>')
    risk_badge.short_description = "Statut"


@admin.register(ProductRecommendation)
class ProductRecommendationAdmin(admin.ModelAdmin):
    list_display = [
        'source_product', 'recommended_product', 'recommendation_type_badge',
        'confidence_badge', 'times_bought_together', 'is_active'
    ]
    list_filter = ['recommendation_type', 'is_active']
    search_fields = ['source_product__name', 'recommended_product__name']
    
    def recommendation_type_badge(self, obj):
        colors = {
            'frequently_bought_together': '#28a745',
            'similar_products': '#007bff',
            'complementary': '#17a2b8',
            'based_on_history': '#6610f2',
            'trending': '#fd7e14'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.recommendation_type, '#6c757d'),
            obj.get_recommendation_type_display()
        )
    recommendation_type_badge.short_description = "Type"
    
    def confidence_badge(self, obj):
        if obj.confidence_score >= 80:
            color = '#28a745'
        elif obj.confidence_score >= 50:
            color = '#ffc107'
        else:
            color = '#dc3545'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.0f}%</span>',
            color, obj.confidence_score
        )
    confidence_badge.short_description = "Confiance"




