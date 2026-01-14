"""
Admin pour E-commerce Pharmacie
Interface d'administration complète avec badges et actions
Application 9
"""
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from django.urls import reverse

from .models import (
    OnlineStore, OnlineProduct, ProductImage, ProductReview,
    Cart, CartItem, OnlineOrder, OnlineOrderItem, OrderStatusHistory,
    PromoCode, PromoCodeUsage, Wishlist, WishlistItem,
    CustomerNotification
)

# Register your models here.


# ============================================================================
# ADMIN CONFIGURATION BOUTIQUE
# ============================================================================

@admin.register(OnlineStore)
class OnlineStoreAdmin(admin.ModelAdmin):
    """Admin pour la boutique en ligne"""
    list_display = [
        'store_name', 'pharmacie', 'delivery_status',
        'payment_methods', 'total_products_display',
        'total_orders_display', 'is_active_badge',
        'maintenance_mode_badge'
    ]
    list_filter = ['is_active', 'maintenance_mode', 'delivery_enabled', 'pickup_enabled']
    search_fields = ['store_name', 'pharmacie__name', 'contact_email', 'contact_phone']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Identification', {
            'fields': ('pharmacie', 'store_name', 'store_description')
        }),
        ('Visuels', {
            'fields': ('store_logo', 'store_banner')
        }),
        ('Livraison', {
            'fields': (
                'delivery_enabled', 'pickup_enabled',
                'delivery_fee', 'free_delivery_threshold',
                'delivery_zones', 'estimated_delivery_time'
            )
        }),
        ('Paiement', {
            'fields': ('payment_on_delivery', 'mobile_money_enabled', 'card_payment_enabled')
        }),
        ('Commande', {
            'fields': ('minimum_order_amount',)
        }),
        ('Contact', {
            'fields': ('contact_email', 'contact_phone', 'whatsapp_number', 'opening_hours')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'classes': ('collapse',)
        }),
        ('Statut', {
            'fields': ('is_active', 'maintenance_mode', 'maintenance_message')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def delivery_status(self, obj):
        methods = []
        if obj.delivery_enabled:
            methods.append('<span style="color: #28a745;">🚚 Livraison</span>')
        if obj.pickup_enabled:
            methods.append('<span style="color: #007bff;">🏪 Retrait</span>')
        return format_html(' | '.join(methods)) if methods else '-'
    delivery_status.short_description = 'Options livraison'
    
    def payment_methods(self, obj):
        methods = []
        if obj.payment_on_delivery:
            methods.append('💵 COD')
        if obj.mobile_money_enabled:
            methods.append('📱 Mobile Money')
        if obj.card_payment_enabled:
            methods.append('💳 Carte')
        return format_html('<br/>'.join(f'<span style="font-size: 11px;">{m}</span>' for m in methods))
    payment_methods.short_description = 'Paiements'
    
    def total_products_display(self, obj):
        count = obj.online_products.filter(is_visible=True).count()
        return format_html('<strong style="color: #007bff;">{} produits</strong>', count)
    total_products_display.short_description = 'Produits'
    
    def total_orders_display(self, obj):
        count = obj.online_orders.count()
        return format_html('<strong style="color: #28a745;">{} commandes</strong>', count)
    total_orders_display.short_description = 'Commandes'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green; font-size: 16px;">✓ Active</span>')
        return format_html('<span style="color: red; font-size: 16px;">✗ Inactive</span>')
    is_active_badge.short_description = 'Statut'
    
    def maintenance_mode_badge(self, obj):
        if obj.maintenance_mode:
            return format_html('<span style="background: #ffc107; color: white; padding: 3px 10px; border-radius: 3px;">🔧 Maintenance</span>')
        return format_html('<span style="color: #28a745;">✓ En ligne</span>')
    maintenance_mode_badge.short_description = 'Mode'


# ============================================================================
# ADMIN PRODUITS EN LIGNE
# ============================================================================

class ProductImageInline(admin.TabularInline):
    """Inline pour les images produit"""
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text', 'display_order']


@admin.register(OnlineProduct)
class OnlineProductAdmin(admin.ModelAdmin):
    """Admin pour les produits en ligne"""
    list_display = [
        'product', 'store', 'current_price_display',
        'promotion_badge', 'stock_badge',
        'visibility_badges', 'statistics_display',
        'created_at'
    ]
    list_filter = [
        'store', 'is_visible', 'is_featured', 'is_new_arrival',
        'is_on_sale', 'requires_prescription', 'created_at'
    ]
    search_fields = ['product__name', 'product__sku', 'online_description']
    autocomplete_fields = ['store', 'product']
    readonly_fields = ['views_count', 'sales_count', 'created_at', 'updated_at']
    inlines = [ProductImageInline]
    
    fieldsets = (
        ('Produit', {
            'fields': ('store', 'product')
        }),
        ('Prix', {
            'fields': ('online_price',)
        }),
        ('Promotion', {
            'fields': ('is_on_sale', 'sale_price', 'sale_start_date', 'sale_end_date')
        }),
        ('Stock', {
            'fields': ('online_stock_quantity', 'max_quantity_per_order')
        }),
        ('Visibilité', {
            'fields': ('is_visible', 'is_featured', 'is_new_arrival')
        }),
        ('Contenu', {
            'fields': (
                'primary_image', 'online_description', 'short_description',
                'usage_instructions', 'warnings', 'storage_conditions'
            )
        }),
        ('Ordonnance', {
            'fields': ('requires_prescription',)
        }),
        ('Statistiques', {
            'fields': ('views_count', 'sales_count'),
            'classes': ('collapse',)
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        ('Disponibilité', {
            'fields': ('available_from', 'available_until', 'display_order')
        })
    )
    
    def current_price_display(self, obj):
        current = obj.get_current_price()
        if obj.is_on_sale and obj.sale_price:
            return format_html(
                '<span style="text-decoration: line-through; color: #6c757d;">{:,.0f}</span><br/>'
                '<strong style="color: #dc3545; font-size: 14px;">{:,.0f} XAF</strong>',
                obj.online_price, current
            )
        return format_html('<strong>{:,.0f} XAF</strong>', current)
    current_price_display.short_description = 'Prix'
    
    def promotion_badge(self, obj):
        if obj.is_on_sale and obj.sale_price:
            discount = obj.get_discount_percentage()
            return format_html(
                '<span style="background: #dc3545; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">-{:.0f}%</span>',
                discount
            )
        return '-'
    promotion_badge.short_description = 'Promo'
    
    def stock_badge(self, obj):
        if obj.online_stock_quantity == 0:
            return format_html('<span style="color: #dc3545; font-weight: bold;">✗ Rupture</span>')
        elif obj.online_stock_quantity <= 10:
            return format_html('<span style="color: #ffc107; font-weight: bold;">⚠️ {} en stock</span>', obj.online_stock_quantity)
        return format_html('<span style="color: #28a745;">✓ {} en stock</span>', obj.online_stock_quantity)
    stock_badge.short_description = 'Stock'
    
    def visibility_badges(self, obj):
        badges = []
        if obj.is_featured:
            badges.append('<span style="background: #ffc107; color: white; padding: 2px 8px; border-radius: 3px; font-size: 10px;">⭐ VEDETTE</span>')
        if obj.is_new_arrival:
            badges.append('<span style="background: #28a745; color: white; padding: 2px 8px; border-radius: 3px; font-size: 10px;">🆕 NOUVEAU</span>')
        if obj.requires_prescription:
            badges.append('<span style="background: #dc3545; color: white; padding: 2px 8px; border-radius: 3px; font-size: 10px;">📋 ORDONNANCE</span>')
        if not obj.is_visible:
            badges.append('<span style="background: #6c757d; color: white; padding: 2px 8px; border-radius: 3px; font-size: 10px;">👁️ MASQUÉ</span>')
        return format_html('<br/>'.join(badges)) if badges else '-'
    visibility_badges.short_description = 'Badges'
    
    def statistics_display(self, obj):
        return format_html(
            '<small>{} vues<br/>{} ventes</small>',
            obj.views_count, obj.sales_count
        )
    statistics_display.short_description = 'Stats'
    
    actions = ['mark_as_featured', 'mark_as_new_arrival', 'mark_out_of_stock']
    
    def mark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} produit(s) marqué(s) comme vedette.')
    mark_as_featured.short_description = 'Marquer comme vedette'
    
    def mark_as_new_arrival(self, request, queryset):
        updated = queryset.update(is_new_arrival=True)
        self.message_user(request, f'{updated} produit(s) marqué(s) comme nouveauté.')
    mark_as_new_arrival.short_description = 'Marquer comme nouveauté'
    
    def mark_out_of_stock(self, request, queryset):
        updated = queryset.update(online_stock_quantity=0)
        self.message_user(request, f'{updated} produit(s) marqué(s) en rupture.')
    mark_out_of_stock.short_description = 'Marquer en rupture'


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    """Admin pour les avis produits"""
    list_display = [
        'created_at', 'customer', 'online_product',
        'rating_badge', 'verified_badge',
        'is_approved_badge', 'helpful_count'
    ]
    list_filter = ['rating', 'is_approved', 'verified_purchase', 'created_at']
    search_fields = ['customer__first_name', 'customer__last_name', 'title', 'comment']
    autocomplete_fields = ['online_product', 'customer', 'moderated_by']
    readonly_fields = ['verified_purchase', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Avis', {
            'fields': ('online_product', 'customer')
        }),
        ('Évaluation', {
            'fields': ('rating', 'title', 'comment')
        }),
        ('Vérification', {
            'fields': ('verified_purchase',)
        }),
        ('Modération', {
            'fields': ('is_approved', 'moderated_by', 'moderation_notes')
        }),
        ('Statistiques', {
            'fields': ('helpful_count',)
        })
    )
    
    def rating_badge(self, obj):
        stars = '⭐' * obj.rating
        colors = {1: '#dc3545', 2: '#fd7e14', 3: '#ffc107', 4: '#28a745', 5: '#007bff'}
        color = colors.get(obj.rating, '#6c757d')
        return format_html('<span style="color: {}; font-size: 14px;">{}</span>', color, stars)
    rating_badge.short_description = 'Note'
    
    def verified_badge(self, obj):
        if obj.verified_purchase:
            return format_html('<span style="color: #28a745; font-weight: bold;">✓ Achat vérifié</span>')
        return '-'
    verified_badge.short_description = 'Vérifié'
    
    def is_approved_badge(self, obj):
        if obj.is_approved:
            return format_html('<span style="color: green;">✓ Approuvé</span>')
        return format_html('<span style="color: orange;">⏳ En attente</span>')
    is_approved_badge.short_description = 'Modération'
    
    actions = ['approve_reviews', 'reject_reviews']
    
    def approve_reviews(self, request, queryset):
        updated = queryset.update(is_approved=True, moderated_by=request.user)
        self.message_user(request, f'{updated} avis approuvé(s).')
    approve_reviews.short_description = 'Approuver'
    
    def reject_reviews(self, request, queryset):
        updated = queryset.update(is_approved=False, moderated_by=request.user)
        self.message_user(request, f'{updated} avis rejeté(s).')
    reject_reviews.short_description = 'Rejeter'


# ============================================================================
# ADMIN PANIER
# ============================================================================

class CartItemInline(admin.TabularInline):
    """Inline pour les articles du panier"""
    model = CartItem
    extra = 0
    readonly_fields = ['unit_price', 'created_at', 'updated_at']
    fields = ['online_product', 'quantity', 'unit_price']
    can_delete = True


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """Admin pour les paniers"""
    list_display = [
        'customer', 'store', 'total_items_display',
        'subtotal_display', 'is_active_badge',
        'abandoned_badge', 'updated_at'
    ]
    list_filter = ['store', 'is_active', 'created_at', 'updated_at']
    search_fields = ['customer__first_name', 'customer__last_name', 'session_key']
    autocomplete_fields = ['store', 'customer']
    readonly_fields = ['created_at', 'updated_at', 'abandoned_at']
    inlines = [CartItemInline]
    
    def total_items_display(self, obj):
        count = obj.get_total_items()
        return format_html('<strong>{} article(s)</strong>', count)
    total_items_display.short_description = 'Articles'
    
    def subtotal_display(self, obj):
        subtotal = obj.get_subtotal()
        return format_html('<strong style="color: #28a745;">{:,.0f} XAF</strong>', subtotal)
    subtotal_display.short_description = 'Sous-total'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Actif</span>')
        return format_html('<span style="color: #6c757d;">Inactif</span>')
    is_active_badge.short_description = 'Statut'
    
    def abandoned_badge(self, obj):
        if obj.abandoned_at:
            days = (timezone.now() - obj.abandoned_at).days
            return format_html('<span style="color: #dc3545;">⚠️ Abandonné ({}j)</span>', days)
        return '-'
    abandoned_badge.short_description = 'Abandon'


# ============================================================================
# ADMIN COMMANDES
# ============================================================================

class OnlineOrderItemInline(admin.TabularInline):
    """Inline pour les articles de commande"""
    model = OnlineOrderItem
    extra = 0
    readonly_fields = ['product_name', 'product_sku', 'unit_price', 'subtotal', 'created_at']
    fields = ['online_product', 'product_name', 'product_sku', 'quantity', 'unit_price', 'subtotal']
    can_delete = False


class OrderStatusHistoryInline(admin.TabularInline):
    """Inline pour l'historique des statuts"""
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ['status', 'comment', 'changed_by', 'customer_notified', 'created_at']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(OnlineOrder)
class OnlineOrderAdmin(admin.ModelAdmin):
    """Admin pour les commandes en ligne"""
    list_display = [
        'order_number', 'customer', 'status_badge',
        'payment_badge', 'delivery_method_badge',
        'total_display', 'prescription_badge',
        'created_at'
    ]
    list_filter = [
        'status', 'payment_status', 'delivery_method',
        'prescription_required', 'prescription_verified',
        'created_at'
    ]
    search_fields = [
        'order_number', 'customer__first_name', 'customer__last_name',
        'email', 'phone', 'delivery_city'
    ]
    autocomplete_fields = ['store', 'customer', 'promo_code', 'confirmed_by', 'sale']
    readonly_fields = [
        'order_number', 'created_at', 'updated_at',
        'confirmed_at', 'shipped_at', 'delivered_at', 'cancelled_at', 'paid_at'
    ]
    inlines = [OnlineOrderItemInline, OrderStatusHistoryInline]
    
    fieldsets = (
        ('Commande', {
            'fields': ('store', 'order_number', 'customer')
        }),
        ('Contact', {
            'fields': ('email', 'phone')
        }),
        ('Statut', {
            'fields': ('status',)
        }),
        ('Livraison', {
            'fields': (
                'delivery_method', 'delivery_address', 'delivery_city',
                'delivery_zone', 'delivery_instructions'
            )
        }),
        ('Paiement', {
            'fields': (
                'payment_method', 'payment_status',
                'payment_reference', 'paid_at'
            )
        }),
        ('Montants', {
            'fields': ('subtotal', 'delivery_fee', 'discount_amount', 'total')
        }),
        ('Code promo', {
            'fields': ('promo_code',)
        }),
        ('Ordonnance', {
            'fields': (
                'prescription_required', 'prescription_file',
                'prescription_verified'
            )
        }),
        ('Notes', {
            'fields': ('customer_notes', 'admin_notes')
        }),
        ('Traçabilité', {
            'fields': (
                'confirmed_at', 'confirmed_by',
                'shipped_at', 'delivered_at',
                'cancelled_at', 'cancellation_reason'
            ),
            'classes': ('collapse',)
        }),
        ('Vente liée', {
            'fields': ('sale',),
            'classes': ('collapse',)
        })
    )
    
    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'confirmed': '#28a745',
            'processing': '#007bff',
            'ready': '#17a2b8',
            'shipped': '#6f42c1',
            'delivered': '#28a745',
            'cancelled': '#dc3545',
            'refunded': '#fd7e14'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 5px 12px; border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Statut'
    
    def payment_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'paid': '#28a745',
            'failed': '#dc3545',
            'refunded': '#fd7e14'
        }
        icons = {
            'pending': '⏳',
            'paid': '✓',
            'failed': '✗',
            'refunded': '↩️'
        }
        color = colors.get(obj.payment_status, '#6c757d')
        icon = icons.get(obj.payment_status, '●')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_payment_status_display()
        )
    payment_badge.short_description = 'Paiement'
    
    def delivery_method_badge(self, obj):
        if obj.delivery_method == 'delivery':
            return format_html('<span style="color: #007bff;">🚚 Livraison</span>')
        return format_html('<span style="color: #28a745;">🏪 Retrait</span>')
    delivery_method_badge.short_description = 'Livraison'
    
    def total_display(self, obj):
        return format_html(
            '<strong style="color: #28a745; font-size: 14px;">{:,.0f} XAF</strong><br/>'
            '<small>ST: {:,.0f} | Liv: {:,.0f} | Promo: {:,.0f}</small>',
            obj.total, obj.subtotal, obj.delivery_fee, obj.discount_amount
        )
    total_display.short_description = 'Total'
    
    def prescription_badge(self, obj):
        if obj.prescription_required:
            if obj.prescription_verified:
                return format_html('<span style="color: #28a745;">✓ Vérifiée</span>')
            elif obj.prescription_file:
                return format_html('<span style="color: #ffc107;">⏳ À vérifier</span>')
            return format_html('<span style="color: #dc3545;">✗ Manquante</span>')
        return '-'
    prescription_badge.short_description = 'Ordonnance'
    
    actions = ['confirm_orders', 'mark_as_shipped', 'mark_as_delivered', 'cancel_orders']
    
    def confirm_orders(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='confirmed',
            confirmed_at=timezone.now(),
            confirmed_by=request.user
        )
        self.message_user(request, f'{updated} commande(s) confirmée(s).')
    confirm_orders.short_description = 'Confirmer les commandes'
    
    def mark_as_shipped(self, request, queryset):
        updated = queryset.filter(status='ready').update(
            status='shipped',
            shipped_at=timezone.now()
        )
        self.message_user(request, f'{updated} commande(s) expédiée(s).')
    mark_as_shipped.short_description = 'Marquer comme expédiée'
    
    def mark_as_delivered(self, request, queryset):
        updated = queryset.filter(status='shipped').update(
            status='delivered',
            delivered_at=timezone.now()
        )
        self.message_user(request, f'{updated} commande(s) livrée(s).')
    mark_as_delivered.short_description = 'Marquer comme livrée'
    
    def cancel_orders(self, request, queryset):
        updated = queryset.filter(status__in=['pending', 'confirmed']).update(
            status='cancelled',
            cancelled_at=timezone.now()
        )
        self.message_user(request, f'{updated} commande(s) annulée(s).')
    cancel_orders.short_description = 'Annuler les commandes'


# ============================================================================
# ADMIN CODES PROMO
# ============================================================================

@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    """Admin pour les codes promo"""
    list_display = [
        'code', 'store', 'discount_badge',
        'validity_badge', 'usage_display',
        'is_active_badge'
    ]
    list_filter = ['discount_type', 'is_active', 'valid_from', 'valid_until']
    search_fields = ['code', 'description']
    autocomplete_fields = ['store', 'created_by', 'applicable_categories', 'applicable_products']
    readonly_fields = ['times_used', 'created_at']
    filter_horizontal = ['applicable_categories', 'applicable_products']
    
    fieldsets = (
        ('Code', {
            'fields': ('store', 'code', 'description')
        }),
        ('Réduction', {
            'fields': ('discount_type', 'discount_value', 'max_discount_amount')
        }),
        ('Conditions', {
            'fields': ('min_purchase_amount',)
        }),
        ('Limites', {
            'fields': ('usage_limit', 'usage_limit_per_customer', 'times_used')
        }),
        ('Validité', {
            'fields': ('valid_from', 'valid_until')
        }),
        ('Restrictions', {
            'fields': ('applicable_categories', 'applicable_products'),
            'classes': ('collapse',)
        }),
        ('Statut', {
            'fields': ('is_active',)
        })
    )
    
    def discount_badge(self, obj):
        if obj.discount_type == 'percentage':
            return format_html(
                '<span style="background: #28a745; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}%</span>',
                obj.discount_value
            )
        elif obj.discount_type == 'fixed':
            return format_html(
                '<span style="background: #007bff; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{:,.0f} XAF</span>',
                obj.discount_value
            )
        return format_html('<span style="background: #ffc107; color: white; padding: 3px 10px; border-radius: 3px;">🚚 Gratuit</span>')
    discount_badge.short_description = 'Réduction'
    
    def validity_badge(self, obj):
        now = timezone.now()
        if obj.valid_from > now:
            return format_html('<span style="color: #6c757d;">Pas encore actif</span>')
        elif obj.valid_until < now:
            return format_html('<span style="color: #dc3545;">✗ Expiré</span>')
        return format_html('<span style="color: #28a745;">✓ Valide</span>')
    validity_badge.short_description = 'Validité'
    
    def usage_display(self, obj):
        if obj.usage_limit:
            percentage = (obj.times_used / obj.usage_limit) * 100
            color = '#28a745' if percentage < 75 else '#ffc107' if percentage < 90 else '#dc3545'
            return format_html(
                '<strong style="color: {};">{} / {}</strong><br/>'
                '<small>({:.0f}%)</small>',
                color, obj.times_used, obj.usage_limit, percentage
            )
        return format_html('<strong>{}</strong> fois', obj.times_used)
    usage_display.short_description = 'Utilisation'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Actif</span>')
        return format_html('<span style="color: red;">✗ Inactif</span>')
    is_active_badge.short_description = 'Statut'


# ============================================================================
# ADMIN LISTE DE SOUHAITS
# ============================================================================

class WishlistItemInline(admin.TabularInline):
    """Inline pour les articles de la wishlist"""
    model = WishlistItem
    extra = 0
    readonly_fields = ['added_at']
    fields = ['online_product', 'notify_on_price_drop', 'notify_on_availability', 'added_at']


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    """Admin pour les listes de souhaits"""
    list_display = ['customer', 'total_items_display', 'created_at', 'updated_at']
    search_fields = ['customer__first_name', 'customer__last_name']
    autocomplete_fields = ['customer']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [WishlistItemInline]
    
    def total_items_display(self, obj):
        count = obj.get_total_items()
        return format_html('<strong>{} article(s)</strong>', count)
    total_items_display.short_description = 'Articles'


# ============================================================================
# ADMIN NOTIFICATIONS
# ============================================================================

@admin.register(CustomerNotification)
class CustomerNotificationAdmin(admin.ModelAdmin):
    """Admin pour les notifications client"""
    list_display = [
        'created_at', 'customer', 'notification_type_badge',
        'title', 'send_channels', 'is_read_badge'
    ]
    list_filter = [
        'notification_type', 'is_read',
        'sent_via_email', 'sent_via_sms', 'sent_via_push',
        'created_at'
    ]
    search_fields = ['customer__first_name', 'customer__last_name', 'title', 'message']
    autocomplete_fields = ['customer', 'order', 'online_product']
    readonly_fields = ['created_at', 'read_at']
    
    def notification_type_badge(self, obj):
        colors = {
            'order_confirmed': '#28a745',
            'order_shipped': '#007bff',
            'order_delivered': '#17a2b8',
            'order_cancelled': '#dc3545',
            'price_drop': '#ffc107',
            'back_in_stock': '#28a745',
            'promo_code': '#e83e8c',
            'abandoned_cart': '#fd7e14',
        }
        icons = {
            'order_confirmed': '✓',
            'order_shipped': '🚚',
            'order_delivered': '🎉',
            'order_cancelled': '✗',
            'price_drop': '💰',
            'back_in_stock': '📦',
            'promo_code': '🎁',
            'abandoned_cart': '🛒',
        }
        color = colors.get(obj.notification_type, '#6c757d')
        icon = icons.get(obj.notification_type, '🔔')
        return format_html(
            '<span style="color: {};">{} {}</span>',
            color, icon, obj.get_notification_type_display()
        )
    notification_type_badge.short_description = 'Type'
    
    def send_channels(self, obj):
        channels = []
        if obj.sent_via_email:
            channels.append('📧')
        if obj.sent_via_sms:
            channels.append('📱')
        if obj.sent_via_push:
            channels.append('🔔')
        return format_html(' '.join(channels)) if channels else '-'
    send_channels.short_description = 'Canaux'
    
    def is_read_badge(self, obj):
        if obj.is_read:
            return format_html('<span style="color: #28a745;">✓ Lu</span>')
        return format_html('<span style="color: #ffc107;">⏳ Non lu</span>')
    is_read_badge.short_description = 'Statut'

