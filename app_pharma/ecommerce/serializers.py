"""
Serializers pour E-commerce Pharmacie
API REST complète pour la boutique en ligne
Application 9
"""
from rest_framework import serializers
from django.db.models import Avg, Count, Sum
from decimal import Decimal

from .models import (
    OnlineStore, OnlineProduct, ProductImage, ProductReview,
    Cart, CartItem, OnlineOrder, OnlineOrderItem, OrderStatusHistory,
    PromoCode, PromoCodeUsage, Wishlist, WishlistItem,
    CustomerNotification
)


# ============================================================================
# SERIALIZERS CONFIGURATION BOUTIQUE
# ============================================================================

class OnlineStoreSerializer(serializers.ModelSerializer):
    """Serializer pour la boutique en ligne"""
    pharmacie_name = serializers.CharField(source='pharmacie.name', read_only=True)
    total_products = serializers.SerializerMethodField()
    total_orders = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    
    class Meta:
        model = OnlineStore
        fields = [
            'id', 'pharmacie', 'pharmacie_name',
            'store_name', 'store_description',
            'store_logo', 'store_banner',
            'delivery_enabled', 'pickup_enabled',
            'delivery_fee', 'free_delivery_threshold',
            'delivery_zones', 'estimated_delivery_time',
            'payment_on_delivery', 'mobile_money_enabled', 'card_payment_enabled',
            'minimum_order_amount',
            'contact_email', 'contact_phone', 'whatsapp_number',
            'opening_hours',
            'meta_title', 'meta_description', 'meta_keywords',
            'is_active', 'maintenance_mode', 'maintenance_message',
            'total_products', 'total_orders', 'average_rating',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_total_products(self, obj):
        """Nombre de produits visibles"""
        return obj.online_products.filter(is_visible=True).count()
    
    def get_total_orders(self, obj):
        """Nombre total de commandes"""
        return obj.online_orders.count()
    
    def get_average_rating(self, obj):
        """Note moyenne des produits"""
        avg = ProductReview.objects.filter(
            online_product__store=obj,
            is_approved=True
        ).aggregate(avg_rating=Avg('rating'))['avg_rating']
        return round(avg, 2) if avg else 0


# ============================================================================
# SERIALIZERS PRODUITS
# ============================================================================

class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer pour les images produit"""
    
    class Meta:
        model = ProductImage
        fields = [
            'id', 'online_product', 'image', 'alt_text',
            'display_order', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ProductReviewSerializer(serializers.ModelSerializer):
    """Serializer pour les avis produits"""
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    moderated_by_name = serializers.CharField(source='moderated_by.get_full_name', read_only=True)
    rating_display = serializers.CharField(source='get_rating_display', read_only=True)
    
    class Meta:
        model = ProductReview
        fields = [
            'id', 'online_product',
            'customer', 'customer_name',
            'rating', 'rating_display',
            'title', 'comment',
            'verified_purchase',
            'is_approved', 'moderated_by', 'moderated_by_name', 'moderation_notes',
            'helpful_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'verified_purchase', 'created_at', 'updated_at']


class OnlineProductListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour liste de produits"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    category_name = serializers.CharField(source='product.category.name', read_only=True)
    current_price = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()
    is_available = serializers.SerializerMethodField()
    
    class Meta:
        model = OnlineProduct
        fields = [
            'id', 'product', 'product_name', 'product_sku', 'category_name',
            'online_price', 'current_price',
            'is_on_sale', 'sale_price', 'discount_percentage',
            'online_stock_quantity', 'is_available',
            'is_visible', 'is_featured', 'is_new_arrival',
            'primary_image', 'short_description',
            'requires_prescription',
            'average_rating', 'reviews_count', 'views_count', 'sales_count',
            'created_at'
        ]
    
    def get_current_price(self, obj):
        """Prix actuel (avec promo si applicable)"""
        return float(obj.get_current_price())
    
    def get_discount_percentage(self, obj):
        """Pourcentage de réduction"""
        return obj.get_discount_percentage()
    
    def get_average_rating(self, obj):
        """Note moyenne"""
        avg = obj.reviews.filter(is_approved=True).aggregate(
            avg_rating=Avg('rating')
        )['avg_rating']
        return round(avg, 2) if avg else 0
    
    def get_reviews_count(self, obj):
        """Nombre d'avis"""
        return obj.reviews.filter(is_approved=True).count()
    
    def get_is_available(self, obj):
        """Disponibilité"""
        return obj.online_stock_quantity > 0 and obj.is_visible


class OnlineProductDetailSerializer(serializers.ModelSerializer):
    """Serializer complet pour détail produit"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    product_description = serializers.CharField(source='product.description', read_only=True)
    category = serializers.CharField(source='product.category.name', read_only=True)
    current_price = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()
    
    # Relations imbriquées
    additional_images = ProductImageSerializer(many=True, read_only=True)
    reviews = ProductReviewSerializer(many=True, read_only=True)
    
    # Statistiques
    average_rating = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()
    is_available = serializers.SerializerMethodField()
    
    class Meta:
        model = OnlineProduct
        fields = [
            'id', 'store', 'product', 'product_name', 'product_sku',
            'product_description', 'category',
            'online_price', 'current_price',
            'is_on_sale', 'sale_price', 'sale_start_date', 'sale_end_date',
            'discount_percentage',
            'online_stock_quantity', 'max_quantity_per_order', 'is_available',
            'is_visible', 'is_featured', 'is_new_arrival',
            'primary_image', 'additional_images',
            'online_description', 'short_description',
            'usage_instructions', 'warnings', 'storage_conditions',
            'requires_prescription',
            'views_count', 'sales_count',
            'average_rating', 'reviews_count', 'reviews',
            'meta_title', 'meta_description',
            'available_from', 'available_until', 'display_order',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'views_count', 'sales_count', 'created_at', 'updated_at']
    
    def get_current_price(self, obj):
        return float(obj.get_current_price())
    
    def get_discount_percentage(self, obj):
        return obj.get_discount_percentage()
    
    def get_average_rating(self, obj):
        avg = obj.reviews.filter(is_approved=True).aggregate(
            avg_rating=Avg('rating')
        )['avg_rating']
        return round(avg, 2) if avg else 0
    
    def get_reviews_count(self, obj):
        return obj.reviews.filter(is_approved=True).count()
    
    def get_is_available(self, obj):
        return obj.online_stock_quantity > 0 and obj.is_visible


# ============================================================================
# SERIALIZERS PANIER
# ============================================================================

class CartItemSerializer(serializers.ModelSerializer):
    """Serializer pour les articles du panier"""
    product_name = serializers.CharField(source='online_product.product.name', read_only=True)
    product_image = serializers.ImageField(source='online_product.primary_image', read_only=True)
    current_price = serializers.SerializerMethodField()
    line_total = serializers.SerializerMethodField()
    is_available = serializers.SerializerMethodField()
    
    class Meta:
        model = CartItem
        fields = [
            'id', 'cart', 'online_product',
            'product_name', 'product_image',
            'quantity', 'unit_price', 'current_price',
            'line_total', 'is_available',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_current_price(self, obj):
        """Prix actuel du produit"""
        return float(obj.online_product.get_current_price())
    
    def get_line_total(self, obj):
        """Total de la ligne"""
        return float(obj.get_line_total())
    
    def get_is_available(self, obj):
        """Vérifier disponibilité"""
        return (obj.online_product.online_stock_quantity >= obj.quantity and 
                obj.online_product.is_visible)


class CartSerializer(serializers.ModelSerializer):
    """Serializer pour le panier"""
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()
    delivery_fee = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart
        fields = [
            'id', 'store', 'customer', 'customer_name',
            'session_key', 'is_active',
            'items', 'total_items', 'subtotal', 'delivery_fee', 'total',
            'created_at', 'updated_at', 'abandoned_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'abandoned_at']
    
    def get_total_items(self, obj):
        return obj.get_total_items()
    
    def get_subtotal(self, obj):
        return float(obj.get_subtotal())
    
    def get_delivery_fee(self, obj):
        subtotal = obj.get_subtotal()
        if obj.store.delivery_enabled:
            if subtotal < obj.store.free_delivery_threshold:
                return float(obj.store.delivery_fee)
        return 0.0
    
    def get_total(self, obj):
        return float(obj.get_total())


# ============================================================================
# SERIALIZERS COMMANDES
# ============================================================================

class OnlineOrderItemSerializer(serializers.ModelSerializer):
    """Serializer pour les articles de commande"""
    
    class Meta:
        model = OnlineOrderItem
        fields = [
            'id', 'order', 'online_product',
            'product_name', 'product_sku',
            'quantity', 'unit_price', 'subtotal',
            'was_on_sale', 'original_price',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    """Serializer pour l'historique des statuts"""
    changed_by_name = serializers.CharField(source='changed_by.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = OrderStatusHistory
        fields = [
            'id', 'order', 'status', 'status_display',
            'comment', 'changed_by', 'changed_by_name',
            'customer_notified', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class OnlineOrderListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour liste de commandes"""
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = OnlineOrder
        fields = [
            'id', 'order_number', 'store',
            'customer', 'customer_name',
            'status', 'status_display',
            'payment_status', 'payment_status_display',
            'delivery_method',
            'subtotal', 'delivery_fee', 'discount_amount', 'total',
            'items_count',
            'created_at', 'updated_at'
        ]
    
    def get_items_count(self, obj):
        return obj.items.count()


class OnlineOrderDetailSerializer(serializers.ModelSerializer):
    """Serializer complet pour détail commande"""
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    customer_email = serializers.EmailField(source='customer.email', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone', read_only=True)
    
    confirmed_by_name = serializers.CharField(source='confirmed_by.get_full_name', read_only=True)
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    delivery_method_display = serializers.CharField(source='get_delivery_method_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    
    # Relations imbriquées
    items = OnlineOrderItemSerializer(many=True, read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    
    promo_code_code = serializers.CharField(source='promo_code.code', read_only=True)
    
    class Meta:
        model = OnlineOrder
        fields = [
            'id', 'store', 'order_number',
            'customer', 'customer_name', 'customer_email', 'customer_phone',
            'email', 'phone',
            'status', 'status_display',
            'delivery_method', 'delivery_method_display',
            'delivery_address', 'delivery_city', 'delivery_zone', 'delivery_instructions',
            'payment_method', 'payment_method_display',
            'payment_status', 'payment_status_display',
            'payment_reference', 'paid_at',
            'subtotal', 'delivery_fee', 'discount_amount', 'total',
            'promo_code', 'promo_code_code',
            'prescription_required', 'prescription_file', 'prescription_verified',
            'customer_notes', 'admin_notes',
            'confirmed_at', 'confirmed_by', 'confirmed_by_name',
            'shipped_at', 'delivered_at',
            'cancelled_at', 'cancellation_reason',
            'sale',
            'items', 'status_history',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'order_number', 'created_at', 'updated_at']


# ============================================================================
# SERIALIZERS CODES PROMO
# ============================================================================

class PromoCodeSerializer(serializers.ModelSerializer):
    """Serializer pour les codes promo"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    discount_type_display = serializers.CharField(source='get_discount_type_display', read_only=True)
    is_valid = serializers.SerializerMethodField()
    times_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = PromoCode
        fields = [
            'id', 'store', 'code', 'description',
            'discount_type', 'discount_type_display', 'discount_value',
            'min_purchase_amount', 'max_discount_amount',
            'usage_limit', 'usage_limit_per_customer', 'times_used', 'times_remaining',
            'valid_from', 'valid_until',
            'applicable_categories', 'applicable_products',
            'is_active', 'is_valid',
            'created_at', 'created_by', 'created_by_name'
        ]
        read_only_fields = ['id', 'times_used', 'created_at']
    
    def get_is_valid(self, obj):
        """Vérifier si le code est valide"""
        return obj.is_valid()
    
    def get_times_remaining(self, obj):
        """Nombre d'utilisations restantes"""
        if obj.usage_limit:
            return max(0, obj.usage_limit - obj.times_used)
        return None


class PromoCodeUsageSerializer(serializers.ModelSerializer):
    """Serializer pour l'utilisation des codes promo"""
    promo_code_code = serializers.CharField(source='promo_code.code', read_only=True)
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    
    class Meta:
        model = PromoCodeUsage
        fields = [
            'id', 'promo_code', 'promo_code_code',
            'customer', 'customer_name',
            'order', 'order_number',
            'discount_amount', 'used_at'
        ]
        read_only_fields = ['id', 'used_at']


# ============================================================================
# SERIALIZERS LISTE DE SOUHAITS
# ============================================================================

class WishlistItemSerializer(serializers.ModelSerializer):
    """Serializer pour les articles de la liste de souhaits"""
    product_name = serializers.CharField(source='online_product.product.name', read_only=True)
    product_image = serializers.ImageField(source='online_product.primary_image', read_only=True)
    current_price = serializers.SerializerMethodField()
    is_on_sale = serializers.BooleanField(source='online_product.is_on_sale', read_only=True)
    is_available = serializers.SerializerMethodField()
    
    class Meta:
        model = WishlistItem
        fields = [
            'id', 'wishlist', 'online_product',
            'product_name', 'product_image',
            'current_price', 'is_on_sale', 'is_available',
            'notify_on_price_drop', 'notify_on_availability',
            'added_at'
        ]
        read_only_fields = ['id', 'added_at']
    
    def get_current_price(self, obj):
        return float(obj.online_product.get_current_price())
    
    def get_is_available(self, obj):
        return obj.online_product.online_stock_quantity > 0


class WishlistSerializer(serializers.ModelSerializer):
    """Serializer pour la liste de souhaits"""
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    items = WishlistItemSerializer(many=True, read_only=True)
    total_items = serializers.SerializerMethodField()
    
    class Meta:
        model = Wishlist
        fields = [
            'id', 'customer', 'customer_name',
            'items', 'total_items',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_total_items(self, obj):
        return obj.get_total_items()


# ============================================================================
# SERIALIZERS NOTIFICATIONS
# ============================================================================

class CustomerNotificationSerializer(serializers.ModelSerializer):
    """Serializer pour les notifications client"""
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    product_name = serializers.CharField(source='online_product.product.name', read_only=True)
    
    class Meta:
        model = CustomerNotification
        fields = [
            'id', 'customer', 'customer_name',
            'notification_type', 'notification_type_display',
            'title', 'message',
            'order', 'order_number',
            'online_product', 'product_name',
            'is_read', 'read_at',
            'sent_via_email', 'sent_via_sms', 'sent_via_push',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


# ============================================================================
# SERIALIZERS STATISTIQUES
# ============================================================================

class EcommerceStatsSerializer(serializers.Serializer):
    """Statistiques e-commerce globales"""
    total_products = serializers.IntegerField()
    total_orders = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    pending_orders = serializers.IntegerField()
    completed_orders = serializers.IntegerField()
    average_order_value = serializers.DecimalField(max_digits=12, decimal_places=2)
    conversion_rate = serializers.FloatField()
    top_products = serializers.ListField()
    recent_reviews = serializers.ListField()
