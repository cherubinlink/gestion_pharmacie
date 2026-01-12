"""
Configuration de l'interface d'administration Django
pour la gestion de stock et approvisionnements
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Sum, Q, F
from django.utils import timezone
from datetime import timedelta

from gestion_stock.models import (
    # Fournisseurs et Stock
    Supplier, StorageLocation, Batch, StockItem, StockMovement,
    # Commandes
    PurchaseOrder, PurchaseOrderItem, Reception, ReceptionItem,
    # Inventaires
    Inventory, InventoryCount,
    # IA et Prévisions
    StockForecast, ReorderRule, StockAlert
)

# Register your models here.

# Personnalisation du site admin
admin.site.site_header = "Administration Stock & Approvisionnements"
admin.site.site_title = "Stock Admin"
admin.site.index_title = "Gestion du stock et approvisionnements"



# ============================================================================
# INLINE ADMIN
# ============================================================================

class PurchaseOrderItemInline(admin.TabularInline):
    """Inline pour les lignes de commande"""
    model = PurchaseOrderItem
    extra = 1
    fields = ['product', 'quantity_ordered', 'quantity_received', 'unit_price', 'discount_percentage', 'line_total']
    readonly_fields = ['line_total', 'quantity_received']
    autocomplete_fields = ['product']


class ReceptionItemInline(admin.TabularInline):
    """Inline pour les lignes de réception"""
    model = ReceptionItem
    extra = 0
    fields = ['purchase_order_item', 'quantity_expected', 'quantity_received', 'quantity_accepted', 'batch_number', 'expiry_date', 'is_conform']
    readonly_fields = ['quantity_expected']


class InventoryCountInline(admin.TabularInline):
    """Inline pour les comptages d'inventaire"""
    model = InventoryCount
    extra = 0
    fields = ['product', 'storage_location', 'expected_quantity', 'counted_quantity', 'discrepancy', 'is_verified']
    readonly_fields = ['discrepancy', 'discrepancy_value']
    autocomplete_fields = ['product', 'storage_location']


# ============================================================================
# ADMIN FOURNISSEURS
# ============================================================================

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['supplier_code', 'name', 'supplier_type_badge', 'performance_badge', 'rating_display', 'status_badge', 'total_orders', 'is_preferred']
    list_filter = ['supplier_type', 'status', 'is_preferred', 'pharmacie']
    search_fields = ['name', 'supplier_code', 'email', 'phone']
    readonly_fields = ['supplier_code', 'total_orders', 'on_time_delivery_rate', 'quality_rate', 'created_at', 'updated_at']
    list_per_page = 50
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('pharmacie', 'supplier_code', 'name', 'supplier_type', 'status', 'is_preferred')
        }),
        ('Contact', {
            'fields': ('contact_person', 'email', 'phone', 'mobile', 'fax', 'website')
        }),
        ('Adresse', {
            'fields': ('address', 'city', 'country', 'postal_code')
        }),
        ('Informations légales', {
            'fields': ('tax_id', 'registration_number'),
            'classes': ('collapse',)
        }),
        ('Conditions commerciales', {
            'fields': ('payment_terms', 'min_order_amount', 'delivery_time')
        }),
        ('Performance', {
            'fields': ('rating', 'total_orders', 'on_time_delivery_rate', 'quality_rate')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    def supplier_type_badge(self, obj):
        colors = {
            'manufacturer': '#6610f2',
            'wholesaler': '#20c997',
            'distributor': '#fd7e14',
            'importer': '#17a2b8',
            'other': '#6c757d'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.supplier_type, '#6c757d'),
            obj.get_supplier_type_display()
        )
    supplier_type_badge.short_description = "Type"
    
    def performance_badge(self, obj):
        score = obj.calculate_performance_score()
        if score >= 80:
            color, icon = '#28a745', '⭐⭐⭐'
        elif score >= 60:
            color, icon = '#ffc107', '⭐⭐'
        else:
            color, icon = '#dc3545', '⭐'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {:.1f}%</span>',
            color, icon, score
        )
    performance_badge.short_description = "Performance"
    
    def rating_display(self, obj):
        stars = '⭐' * int(obj.rating)
        return format_html('<span style="font-size: 14px;">{} ({}/5)</span>', stars, obj.rating)
    rating_display.short_description = "Évaluation"
    
    def status_badge(self, obj):
        colors = {'active': '#28a745', 'inactive': '#6c757d', 'blacklisted': '#dc3545'}
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = "Statut"
    
    actions = ['mark_as_preferred', 'activate_suppliers']
    
    def mark_as_preferred(self, request, queryset):
        updated = queryset.update(is_preferred=True)
        self.message_user(request, f'{updated} fournisseur(s) marqué(s) comme préféré(s).')
    mark_as_preferred.short_description = "⭐ Marquer comme préféré"
    
    def activate_suppliers(self, request, queryset):
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} fournisseur(s) activé(s).')
    activate_suppliers.short_description = "✓ Activer"


# ============================================================================
# ADMIN STOCK
# ============================================================================

@admin.register(StorageLocation)
class StorageLocationAdmin(admin.ModelAdmin):
    list_display = ['location_code', 'name', 'location_type_badge', 'occupancy_display', 'temperature_range', 'is_active']
    list_filter = ['location_type', 'is_active', 'pharmacie']
    search_fields = ['name', 'location_code']
    
    def location_type_badge(self, obj):
        icons = {
            'shelf': '🛒', 'reserve': '📦', 'warehouse': '🏭',
            'refrigerator': '❄️', 'freezer': '🧊', 'safe': '🔒', 'other': '📍'
        }
        return format_html('{} {}', icons.get(obj.location_type, ''), obj.get_location_type_display())
    location_type_badge.short_description = "Type"
    
    def occupancy_display(self, obj):
        rate = obj.get_current_occupancy()
        if rate is None:
            return '-'
        color = '#dc3545' if rate >= 90 else '#ffc107' if rate >= 70 else '#28a745'
        return format_html(
            '<div style="width: 100px; background: #e9ecef; border-radius: 3px;">'
            '<div style="width: {}%; background: {}; color: white; padding: 2px; border-radius: 3px; text-align: center;">{:.0f}%</div></div>',
            rate, color, rate
        )
    occupancy_display.short_description = "Occupation"
    
    def temperature_range(self, obj):
        if obj.temperature_min and obj.temperature_max:
            return f"{obj.temperature_min}°C - {obj.temperature_max}°C"
        return '-'
    temperature_range.short_description = "Température"


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ['batch_number', 'product_name', 'expiry_status', 'current_quantity', 'reserved_quantity', 'status_badge', 'supplier_name']
    list_filter = ['status', 'expiry_date', 'supplier']
    search_fields = ['batch_number', 'product__name']
    date_hierarchy = 'expiry_date'
    autocomplete_fields = ['product', 'supplier']
    
    fieldsets = (
        ('Lot', {'fields': ('product', 'batch_number', 'supplier', 'purchase_order')}),
        ('Dates', {'fields': ('manufacturing_date', 'expiry_date')}),
        ('Quantités', {'fields': ('initial_quantity', 'current_quantity', 'reserved_quantity')}),
        ('Coût', {'fields': ('unit_cost',)}),
        ('Statut', {'fields': ('status', 'notes')}),
    )
    
    def product_name(self, obj):
        return obj.product.name
    product_name.short_description = "Produit"
    product_name.admin_order_field = 'product__name'
    
    def expiry_status(self, obj):
        if obj.is_expired():
            return format_html('<span style="color: #dc3545; font-weight: bold;">❌ Expiré</span>')
        days = obj.days_until_expiry()
        if days <= 7:
            color, icon = '#dc3545', '🚨'
        elif days <= 30:
            color, icon = '#ffc107', '⚠️'
        else:
            color, icon = '#28a745', '✓'
        return format_html('<span style="color: {}; font-weight: bold;">{} {} jours</span>', color, icon, days)
    expiry_status.short_description = "Expiration"
    expiry_status.admin_order_field = 'expiry_date'
    
    def status_badge(self, obj):
        colors = {
            'in_stock': '#28a745', 'reserved': '#17a2b8', 'expired': '#dc3545',
            'recalled': '#fd7e14', 'quarantine': '#ffc107'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6c757d'), obj.get_status_display()
        )
    status_badge.short_description = "Statut"
    
    def supplier_name(self, obj):
        return obj.supplier.name if obj.supplier else '-'
    supplier_name.short_description = "Fournisseur"


@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'batch_number', 'location_name', 'quantity', 'expiry_date', 'last_counted_at']
    list_filter = ['storage_location', 'batch__expiry_date']
    search_fields = ['product__name', 'batch__batch_number']
    autocomplete_fields = ['product', 'batch', 'storage_location']
    
    def product_name(self, obj):
        return obj.product.name
    product_name.short_description = "Produit"
    
    def batch_number(self, obj):
        return obj.batch.batch_number
    batch_number.short_description = "Lot"
    
    def location_name(self, obj):
        return obj.storage_location.name
    location_name.short_description = "Emplacement"
    
    def expiry_date(self, obj):
        return obj.batch.expiry_date
    expiry_date.short_description = "Expiration"


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['movement_number', 'movement_type_badge', 'product_name', 'quantity', 'from_location_name', 'to_location_name', 'movement_date', 'performed_by_name']
    list_filter = ['movement_type', 'pharmacie', 'movement_date']
    search_fields = ['movement_number', 'product__name']
    date_hierarchy = 'movement_date'
    readonly_fields = ['movement_number', 'created_at']
    list_per_page = 100
    autocomplete_fields = ['product', 'batch']
    
    def movement_type_badge(self, obj):
        icons = {
            'purchase': '📥', 'sale': '📤', 'transfer': '🔄', 'adjustment': '⚖️',
            'return_supplier': '↩️', 'return_customer': '↪️', 'loss': '❌',
            'damage': '⚠️', 'expiry': '📆', 'inventory': '📋', 'other': '📌'
        }
        colors = {
            'purchase': '#28a745', 'sale': '#17a2b8', 'transfer': '#6610f2',
            'adjustment': '#ffc107', 'loss': '#dc3545', 'damage': '#fd7e14'
        }
        return format_html(
            '<span style="color: {};">{} {}</span>',
            colors.get(obj.movement_type, '#6c757d'),
            icons.get(obj.movement_type, ''),
            obj.get_movement_type_display()
        )
    movement_type_badge.short_description = "Type"
    
    def product_name(self, obj):
        return obj.product.name
    product_name.short_description = "Produit"
    
    def from_location_name(self, obj):
        return obj.from_location.name if obj.from_location else '-'
    from_location_name.short_description = "De"
    
    def to_location_name(self, obj):
        return obj.to_location.name if obj.to_location else '-'
    to_location_name.short_description = "Vers"
    
    def performed_by_name(self, obj):
        return obj.performed_by.get_full_name() if obj.performed_by else '-'
    performed_by_name.short_description = "Par"


# ============================================================================
# ADMIN COMMANDES
# ============================================================================

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'supplier_name', 'order_date', 'expected_delivery_date', 'status_badge', 'priority_badge', 'total_amount_display', 'is_overdue_badge']
    list_filter = ['status', 'priority', 'pharmacie', 'order_date']
    search_fields = ['order_number', 'supplier__name']
    date_hierarchy = 'order_date'
    readonly_fields = ['order_number', 'subtotal', 'tax_amount', 'total_amount', 'sent_at', 'approved_at', 'created_at', 'updated_at']
    inlines = [PurchaseOrderItemInline]
    autocomplete_fields = ['supplier']
    
    fieldsets = (
        ('Commande', {'fields': ('pharmacie', 'order_number', 'supplier', 'status', 'priority')}),
        ('Dates', {'fields': ('order_date', 'expected_delivery_date', 'actual_delivery_date')}),
        ('Montants', {'fields': ('subtotal', 'tax_amount', 'shipping_cost', 'discount_amount', 'total_amount')}),
        ('Livraison', {'fields': ('delivery_address', 'shipping_method', 'tracking_number'), 'classes': ('collapse',)}),
        ('Documents', {'fields': ('pdf_file',), 'classes': ('collapse',)}),
        ('Envoi', {'fields': ('sent_at', 'sent_by', 'sent_method'), 'classes': ('collapse',)}),
        ('Notes', {'fields': ('notes', 'internal_notes'), 'classes': ('collapse',)}),
    )
    
    def supplier_name(self, obj):
        return obj.supplier.name
    supplier_name.short_description = "Fournisseur"
    supplier_name.admin_order_field = 'supplier__name'
    
    def status_badge(self, obj):
        colors = {
            'draft': '#6c757d', 'sent': '#17a2b8', 'confirmed': '#20c997',
            'partially_received': '#ffc107', 'received': '#28a745',
            'cancelled': '#dc3545', 'closed': '#6c757d'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#6c757d'), obj.get_status_display()
        )
    status_badge.short_description = "Statut"
    
    def priority_badge(self, obj):
        colors = {'low': '#17a2b8', 'normal': '#28a745', 'high': '#ffc107', 'urgent': '#dc3545'}
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.priority, '#6c757d'), obj.get_priority_display()
        )
    priority_badge.short_description = "Priorité"
    
    def total_amount_display(self, obj):
        return format_html('<strong style="font-size: 14px; color: green;">{:,.0f} XAF</strong>', obj.total_amount)
    total_amount_display.short_description = "Montant total"
    total_amount_display.admin_order_field = 'total_amount'
    
    def is_overdue_badge(self, obj):
        if obj.is_overdue():
            return format_html('<span style="color: #dc3545; font-weight: bold;">🚨 En retard</span>')
        return format_html('<span style="color: green;">✓ À temps</span>')
    is_overdue_badge.short_description = "Délai"
    
    actions = ['mark_as_sent', 'mark_as_confirmed']
    
    def mark_as_sent(self, request, queryset):
        updated = queryset.filter(status='draft').update(status='sent', sent_at=timezone.now(), sent_by=request.user)
        self.message_user(request, f'{updated} commande(s) marquée(s) comme envoyée(s).')
    mark_as_sent.short_description = "📤 Marquer comme envoyée"
    
    def mark_as_confirmed(self, request, queryset):
        updated = queryset.filter(status='sent').update(status='confirmed')
        self.message_user(request, f'{updated} commande(s) confirmée(s).')
    mark_as_confirmed.short_description = "✓ Confirmer"


@admin.register(Reception)
class ReceptionAdmin(admin.ModelAdmin):
    list_display = ['reception_number', 'order_number', 'reception_date', 'status_badge', 'conformity_display', 'received_by_name']
    list_filter = ['status', 'pharmacie', 'reception_date']
    search_fields = ['reception_number', 'purchase_order__order_number']
    date_hierarchy = 'reception_date'
    readonly_fields = ['reception_number', 'validated_at', 'created_at', 'updated_at']
    inlines = [ReceptionItemInline]
    autocomplete_fields = ['purchase_order']
    
    def order_number(self, obj):
        return obj.purchase_order.order_number
    order_number.short_description = "N° Commande"
    
    def status_badge(self, obj):
        colors = {'in_progress': '#ffc107', 'completed': '#28a745', 'rejected': '#dc3545'}
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6c757d'), obj.get_status_display()
        )
    status_badge.short_description = "Statut"
    
    def conformity_display(self, obj):
        badges = []
        badges.append('<span style="color: green;">✓ Complète</span>' if obj.is_complete else '<span style="color: orange;">⚠️ Incomplète</span>')
        if obj.has_discrepancies:
            badges.append('<span style="color: orange;">⚠️ Écarts</span>')
        if obj.has_damages:
            badges.append('<span style="color: red;">❌ Avaries</span>')
        return format_html(' | '.join(badges))
    conformity_display.short_description = "Conformité"
    
    def received_by_name(self, obj):
        return obj.received_by.get_full_name() if obj.received_by else '-'
    received_by_name.short_description = "Reçu par"
    
    actions = ['validate_receptions']
    
    def validate_receptions(self, request, queryset):
        updated = queryset.filter(status='in_progress').update(status='completed', validated_by=request.user, validated_at=timezone.now())
        self.message_user(request, f'{updated} réception(s) validée(s).')
    validate_receptions.short_description = "✓ Valider"


# ============================================================================
# ADMIN INVENTAIRES
# ============================================================================

@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ['inventory_number', 'inventory_type_badge', 'scheduled_date', 'status_badge', 'progress_display', 'discrepancies_display']
    list_filter = ['inventory_type', 'status', 'pharmacie', 'scheduled_date']
    search_fields = ['inventory_number']
    date_hierarchy = 'scheduled_date'
    readonly_fields = ['inventory_number', 'total_items_counted', 'total_discrepancies', 'value_discrepancy', 'validated_at', 'created_at', 'updated_at']
    inlines = [InventoryCountInline]
    filter_horizontal = ['storage_locations', 'product_categories', 'assigned_to']
    
    def inventory_type_badge(self, obj):
        icons = {'full': '📋', 'partial': '📄', 'cycle': '🔄', 'spot_check': '🔍'}
        return format_html('{} {}', icons.get(obj.inventory_type, ''), obj.get_inventory_type_display())
    inventory_type_badge.short_description = "Type"
    
    def status_badge(self, obj):
        colors = {
            'planned': '#6c757d', 'in_progress': '#ffc107', 'completed': '#17a2b8',
            'validated': '#28a745', 'cancelled': '#dc3545'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6c757d'), obj.get_status_display()
        )
    status_badge.short_description = "Statut"
    
    def progress_display(self, obj):
        return format_html('<strong>{}</strong> items comptés', obj.total_items_counted)
    progress_display.short_description = "Avancement"
    
    def discrepancies_display(self, obj):
        if obj.total_discrepancies == 0:
            return format_html('<span style="color: green;">✓ Aucun écart</span>')
        return format_html(
            '<span style="color: orange; font-weight: bold;">⚠️ {} écart(s) ({:,.0f} XAF)</span>',
            obj.total_discrepancies, obj.value_discrepancy
        )
    discrepancies_display.short_description = "Écarts"
    
    actions = ['start_inventory', 'validate_inventory']
    
    def start_inventory(self, request, queryset):
        updated = queryset.filter(status='planned').update(status='in_progress', start_date=timezone.now())
        self.message_user(request, f'{updated} inventaire(s) démarré(s).')
    start_inventory.short_description = "▶️ Démarrer"
    
    def validate_inventory(self, request, queryset):
        updated = queryset.filter(status='completed').update(status='validated', validated_by=request.user, validated_at=timezone.now())
        self.message_user(request, f'{updated} inventaire(s) validé(s).')
    validate_inventory.short_description = "✓ Valider"


# ============================================================================
# ADMIN IA ET PRÉVISIONS
# ============================================================================

@admin.register(StockForecast)
class StockForecastAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'forecast_date', 'forecast_type_badge', 'predicted_demand', 'confidence_badge', 'stockout_risk_badge', 'recommended_order']
    list_filter = ['forecast_type', 'stockout_risk', 'forecast_date']
    search_fields = ['product__name']
    date_hierarchy = 'forecast_date'
    readonly_fields = ['created_at']
    autocomplete_fields = ['product']
    
    def product_name(self, obj):
        return obj.product.name
    product_name.short_description = "Produit"
    
    def forecast_type_badge(self, obj):
        return format_html(
            '<span style="background: #6610f2; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            obj.get_forecast_type_display()
        )
    forecast_type_badge.short_description = "Type"
    
    def confidence_badge(self, obj):
        color = '#28a745' if obj.confidence_level >= 80 else '#ffc107' if obj.confidence_level >= 60 else '#dc3545'
        return format_html('<span style="color: {}; font-weight: bold;">{:.0f}%</span>', color, obj.confidence_level)
    confidence_badge.short_description = "Confiance"
    
    def stockout_risk_badge(self, obj):
        colors = {'low': '#28a745', 'medium': '#ffc107', 'high': '#fd7e14', 'critical': '#dc3545'}
        icons = {'low': '✓', 'medium': '⚠️', 'high': '🔶', 'critical': '🚨'}
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            colors.get(obj.stockout_risk, '#6c757d'),
            icons.get(obj.stockout_risk, ''),
            obj.get_stockout_risk_display()
        )
    stockout_risk_badge.short_description = "Risque rupture"
    
    def recommended_order(self, obj):
        if obj.recommended_order_quantity > 0:
            return format_html('<strong style="color: #17a2b8;">{} unités</strong>', obj.recommended_order_quantity)
        return '-'
    recommended_order.short_description = "Commande recommandée"


@admin.register(ReorderRule)
class ReorderRuleAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'reorder_method_badge', 'reorder_point', 'reorder_quantity', 'auto_status', 'preferred_supplier_name']
    list_filter = ['reorder_method', 'is_active', 'auto_create_order']
    search_fields = ['product__name']
    autocomplete_fields = ['product', 'preferred_supplier']
    
    def product_name(self, obj):
        return obj.product.name
    product_name.short_description = "Produit"
    
    def reorder_method_badge(self, obj):
        return format_html(
            '<span style="background: #6610f2; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            obj.get_reorder_method_display()
        )
    reorder_method_badge.short_description = "Méthode"
    
    def auto_status(self, obj):
        if obj.auto_create_order:
            return format_html('<span style="color: green; font-weight: bold;">🤖 AUTO</span>')
        return format_html('<span style="color: gray;">Manuel</span>')
    auto_status.short_description = "Mode"
    
    def preferred_supplier_name(self, obj):
        return obj.preferred_supplier.name if obj.preferred_supplier else '-'
    preferred_supplier_name.short_description = "Fournisseur préféré"
    
    actions = ['enable_auto_order', 'disable_auto_order']
    
    def enable_auto_order(self, request, queryset):
        updated = queryset.update(auto_create_order=True, is_active=True)
        self.message_user(request, f'{updated} règle(s) avec création automatique activée(s).')
    enable_auto_order.short_description = "🤖 Activer création auto"
    
    def disable_auto_order(self, request, queryset):
        updated = queryset.update(auto_create_order=False)
        self.message_user(request, f'{updated} règle(s) avec création automatique désactivée(s).')
    disable_auto_order.short_description = "❌ Désactiver création auto"


@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = ['alert_type_badge', 'product_name', 'severity_badge', 'status_badge', 'current_stock', 'created_at']
    list_filter = ['alert_type', 'severity', 'status', 'pharmacie', 'created_at']
    search_fields = ['product__name', 'message']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'acknowledged_at', 'resolved_at']
    list_per_page = 100
    autocomplete_fields = ['product', 'batch']
    
    fieldsets = (
        ('Alerte', {'fields': ('pharmacie', 'alert_type', 'severity', 'status')}),
        ('Produit', {'fields': ('product', 'batch', 'current_stock', 'threshold_value')}),
        ('Message', {'fields': ('message',)}),
        ('Traçabilité', {'fields': ('acknowledged_by', 'acknowledged_at', 'resolved_at'), 'classes': ('collapse',)}),
    )
    
    def alert_type_badge(self, obj):
        icons = {
            'low_stock': '📉', 'out_of_stock': '❌', 'expiring_soon': '⏰',
            'expired': '📆', 'overstock': '📈', 'slow_moving': '🐢', 'reorder_needed': '🔄'
        }
        colors = {
            'low_stock': '#ffc107', 'out_of_stock': '#dc3545', 'expiring_soon': '#fd7e14',
            'expired': '#dc3545', 'overstock': '#17a2b8', 'slow_moving': '#6c757d', 'reorder_needed': '#20c997'
        }
        return format_html(
            '<span style="color: {};">{} {}</span>',
            colors.get(obj.alert_type, '#6c757d'),
            icons.get(obj.alert_type, ''),
            obj.get_alert_type_display()
        )
    alert_type_badge.short_description = "Type"
    
    def product_name(self, obj):
        return obj.product.name
    product_name.short_description = "Produit"
    
    def severity_badge(self, obj):
        colors = {'low': '#17a2b8', 'medium': '#ffc107', 'high': '#fd7e14', 'critical': '#dc3545'}
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(obj.severity, '#6c757d'), obj.get_severity_display()
        )
    severity_badge.short_description = "Sévérité"
    
    def status_badge(self, obj):
        colors = {'active': '#dc3545', 'acknowledged': '#ffc107', 'resolved': '#28a745', 'dismissed': '#6c757d'}
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6c757d'), obj.get_status_display()
        )
    status_badge.short_description = "Statut"
    
    actions = ['acknowledge_alerts', 'resolve_alerts']
    
    def acknowledge_alerts(self, request, queryset):
        updated = queryset.filter(status='active').update(status='acknowledged', acknowledged_by=request.user, acknowledged_at=timezone.now())
        self.message_user(request, f'{updated} alerte(s) prise(s) en compte.')
    acknowledge_alerts.short_description = "✓ Prendre en compte"
    
    def resolve_alerts(self, request, queryset):
        updated = queryset.filter(status__in=['active', 'acknowledged']).update(status='resolved', resolved_at=timezone.now())
        self.message_user(request, f'{updated} alerte(s) résolue(s).')
    resolve_alerts.short_description = "✓ Résoudre"
