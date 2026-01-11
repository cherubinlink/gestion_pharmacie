"""
Serializers pour la gestion des ventes
"""
from rest_framework import serializers
from decimal import Decimal
from django.contrib.auth import get_user_model
from gestion_vente.models import (
    ProductCategory, Product, Promotion, Coupon,
    Sale, SaleItem, Payment, PaymentInstallment,
    ElectronicPrescription, SalesAnalytics, ProductPerformance,
    CustomerPurchasePattern, ProductRecommendation,
    FraudAlert, PurchaseAnomalyLog
)

Utilisateur = get_user_model()


# ============================================================================
# SERIALIZERS PRODUITS
# ============================================================================

class ProductCategorySerializer(serializers.ModelSerializer):
    """Serializer pour les catégories"""
    children_count = serializers.SerializerMethodField()
    products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductCategory
        fields = [
            'id', 'name', 'slug', 'description', 'parent', 'image',
            'is_active', 'display_order', 'children_count', 'products_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_children_count(self, obj):
        return obj.children.filter(is_active=True).count()
    
    def get_products_count(self, obj):
        return obj.products.filter(is_active=True).count()


class ProductSerializer(serializers.ModelSerializer):
    """Serializer pour les produits"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    pharmacie_name = serializers.CharField(source='pharmacie.nom', read_only=True)
    margin = serializers.SerializerMethodField()
    stock_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'pharmacie', 'pharmacie_name', 'name', 'slug', 'category',
            'category_name', 'sku', 'barcode', 'description',
            'active_ingredient', 'dosage', 'pharmaceutical_form', 'manufacturer',
            'purchase_price', 'selling_price', 'tax_rate', 'margin',
            'stock_quantity', 'min_stock_level', 'stock_status',
            'is_available_online', 'requires_prescription',
            'usage_instructions', 'side_effects', 'contraindications',
            'storage_conditions', 'main_image', 'images',
            'is_active', 'is_featured', 'created_by',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_margin(self, obj):
        return obj.calculate_margin()
    
    def get_stock_status(self, obj):
        if obj.is_out_of_stock():
            return 'out_of_stock'
        elif obj.is_low_stock():
            return 'low_stock'
        return 'in_stock'


class ProductListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour la liste de produits"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    stock_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'sku', 'category_name', 'selling_price',
            'stock_quantity', 'stock_status', 'is_available_online',
            'requires_prescription', 'main_image', 'is_active'
        ]
    
    def get_stock_status(self, obj):
        if obj.is_out_of_stock():
            return 'out_of_stock'
        elif obj.is_low_stock():
            return 'low_stock'
        return 'in_stock'


# ============================================================================
# SERIALIZERS PROMOTIONS
# ============================================================================

class PromotionSerializer(serializers.ModelSerializer):
    """Serializer pour les promotions"""
    pharmacie_name = serializers.CharField(source='pharmacie.nom', read_only=True)
    is_valid = serializers.SerializerMethodField()
    in_happy_hours = serializers.SerializerMethodField()
    
    class Meta:
        model = Promotion
        fields = [
            'id', 'pharmacie', 'pharmacie_name', 'name', 'description',
            'promotion_code', 'discount_type', 'discount_value',
            'promotion_scope', 'applicable_products', 'applicable_categories',
            'min_purchase_amount', 'min_quantity', 'max_uses',
            'max_uses_per_customer', 'current_uses', 'start_date',
            'end_date', 'happy_hours_start', 'happy_hours_end',
            'is_active', 'is_stackable', 'is_valid', 'in_happy_hours',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'current_uses', 'created_at', 'updated_at']
    
    def get_is_valid(self, obj):
        return obj.is_valid()
    
    def get_in_happy_hours(self, obj):
        return obj.is_in_happy_hours()


class CouponSerializer(serializers.ModelSerializer):
    """Serializer pour les coupons"""
    pharmacie_name = serializers.CharField(source='pharmacie.nom', read_only=True)
    is_valid = serializers.SerializerMethodField()
    
    class Meta:
        model = Coupon
        fields = [
            'id', 'pharmacie', 'pharmacie_name', 'code', 'discount_type',
            'discount_value', 'min_purchase_amount', 'max_uses',
            'current_uses', 'valid_from', 'valid_until', 'is_active',
            'is_valid', 'created_at'
        ]
        read_only_fields = ['id', 'current_uses', 'created_at']
    
    def get_is_valid(self, obj):
        return obj.is_valid()


# ============================================================================
# SERIALIZERS VENTES
# ============================================================================

class SaleItemSerializer(serializers.ModelSerializer):
    """Serializer pour les lignes de vente"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    
    class Meta:
        model = SaleItem
        fields = [
            'id', 'sale', 'product', 'product_name', 'product_sku',
            'quantity', 'unit_price', 'unit_cost', 'discount_percentage',
            'discount_amount', 'line_subtotal', 'tax_amount', 'line_total',
            'profit_amount', 'applied_promotion', 'created_at'
        ]
        read_only_fields = [
            'id', 'line_subtotal', 'tax_amount', 'line_total',
            'profit_amount', 'created_at'
        ]


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer pour les paiements"""
    payment_method_display = serializers.CharField(
        source='get_payment_method_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    
    class Meta:
        model = Payment
        fields = [
            'id', 'sale', 'payment_method', 'payment_method_display',
            'amount', 'status', 'status_display', 'transaction_id',
            'reference_number', 'is_installment', 'installment_number',
            'total_installments', 'payment_details', 'notes',
            'processed_by', 'payment_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PaymentInstallmentSerializer(serializers.ModelSerializer):
    """Serializer pour les versements"""
    class Meta:
        model = PaymentInstallment
        fields = [
            'id', 'sale', 'installment_number', 'amount', 'due_date',
            'is_paid', 'payment', 'paid_date', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class SaleSerializer(serializers.ModelSerializer):
    """Serializer pour les ventes"""
    items = SaleItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    pharmacie_name = serializers.CharField(source='pharmacie.nom', read_only=True)
    customer_name_display = serializers.SerializerMethodField()
    cashier_name = serializers.CharField(source='cashier.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    total_paid = serializers.SerializerMethodField()
    balance_due = serializers.SerializerMethodField()
    
    class Meta:
        model = Sale
        fields = [
            'id', 'pharmacie', 'pharmacie_name', 'sale_number', 'sale_type',
            'status', 'status_display', 'customer', 'customer_name',
            'customer_name_display', 'customer_phone', 'customer_email',
            'prescription', 'subtotal', 'discount_amount', 'tax_amount',
            'total_amount', 'profit_amount', 'applied_promotions',
            'applied_coupon', 'cashier', 'cashier_name', 'ticket_qr_code',
            'notes', 'internal_notes', 'is_offline_sale', 'synced_at',
            'sale_date', 'completed_at', 'items', 'payments',
            'total_paid', 'balance_due', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'sale_number', 'subtotal', 'discount_amount',
            'tax_amount', 'total_amount', 'profit_amount',
            'created_at', 'updated_at'
        ]
    
    def get_customer_name_display(self, obj):
        if obj.customer:
            return obj.customer.get_full_name()
        return obj.customer_name
    
    def get_total_paid(self, obj):
        return sum(
            p.amount for p in obj.payments.filter(status='completed')
        )
    
    def get_balance_due(self, obj):
        total_paid = self.get_total_paid(obj)
        return obj.total_amount - total_paid


class SaleListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour la liste des ventes"""
    customer_name_display = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Sale
        fields = [
            'id', 'sale_number', 'sale_type', 'status',
            'customer_name_display', 'total_amount', 'profit_amount',
            'sale_date', 'items_count'
        ]
    
    def get_customer_name_display(self, obj):
        if obj.customer:
            return obj.customer.get_full_name()
        return obj.customer_name
    
    def get_items_count(self, obj):
        return obj.items.count()


# ============================================================================
# SERIALIZERS ORDONNANCES
# ============================================================================

class ElectronicPrescriptionSerializer(serializers.ModelSerializer):
    """Serializer pour les ordonnances électroniques"""
    pharmacie_name = serializers.CharField(source='pharmacie.nom', read_only=True)
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    validated_by_name = serializers.CharField(
        source='validated_by.get_full_name',
        read_only=True
    )
    is_expired = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ElectronicPrescription
        fields = [
            'id', 'pharmacie', 'pharmacie_name', 'prescription_number',
            'patient', 'patient_name', 'doctor_name', 'doctor_license',
            'doctor_phone', 'prescription_date', 'expiry_date', 'document',
            'status', 'status_display', 'validated_by', 'validated_by_name',
            'validated_at', 'validation_notes', 'is_duplicate', 'fraud_score',
            'fraud_flags', 'is_expired', 'archived_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'prescription_number', 'validated_by', 'validated_at',
            'is_duplicate', 'fraud_score', 'fraud_flags', 'archived_at',
            'created_at', 'updated_at'
        ]
    
    def get_is_expired(self, obj):
        return obj.is_expired()


# ============================================================================
# SERIALIZERS ANALYTICS
# ============================================================================

class SalesAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer pour les analytics de ventes"""
    pharmacie_name = serializers.CharField(source='pharmacie.nom', read_only=True)
    period_type_display = serializers.CharField(
        source='get_period_type_display',
        read_only=True
    )
    
    class Meta:
        model = SalesAnalytics
        fields = [
            'id', 'pharmacie', 'pharmacie_name', 'period_type',
            'period_type_display', 'period_start', 'period_end',
            'total_sales_count', 'total_revenue', 'total_profit',
            'average_basket', 'total_items_sold', 'unique_products_sold',
            'total_customers', 'new_customers', 'returning_customers',
            'best_selling_product', 'best_revenue_product',
            'revenue_trend', 'profit_margin', 'calculated_at'
        ]
        read_only_fields = ['id', 'calculated_at']


class ProductPerformanceSerializer(serializers.ModelSerializer):
    """Serializer pour la performance des produits"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    
    class Meta:
        model = ProductPerformance
        fields = [
            'id', 'product', 'product_name', 'product_sku',
            'period_start', 'period_end', 'units_sold', 'revenue',
            'profit', 'sales_trend', 'is_declining',
            'restock_recommended', 'recommended_quantity', 'calculated_at'
        ]
        read_only_fields = ['id', 'calculated_at']


class CustomerPurchasePatternSerializer(serializers.ModelSerializer):
    """Serializer pour les comportements d'achat"""
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    pharmacie_name = serializers.CharField(source='pharmacie.nom', read_only=True)
    
    class Meta:
        model = CustomerPurchasePattern
        fields = [
            'id', 'customer', 'customer_name', 'pharmacie', 'pharmacie_name',
            'total_purchases', 'total_spent', 'average_basket_value',
            'favorite_categories', 'favorite_products',
            'average_purchase_frequency', 'last_purchase_date',
            'next_predicted_purchase', 'is_at_risk', 'updated_at'
        ]
        read_only_fields = ['id', 'updated_at']


class ProductRecommendationSerializer(serializers.ModelSerializer):
    """Serializer pour les recommandations de produits"""
    source_product_name = serializers.CharField(source='source_product.name', read_only=True)
    recommended_product_name = serializers.CharField(
        source='recommended_product.name',
        read_only=True
    )
    recommended_product_price = serializers.DecimalField(
        source='recommended_product.selling_price',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    
    class Meta:
        model = ProductRecommendation
        fields = [
            'id', 'source_product', 'source_product_name',
            'recommended_product', 'recommended_product_name',
            'recommended_product_price', 'recommendation_type',
            'confidence_score', 'times_bought_together', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# SERIALIZERS DÉTECTION DE FRAUDE
# ============================================================================

class FraudAlertSerializer(serializers.ModelSerializer):
    """Serializer pour les alertes de fraude"""
    pharmacie_name = serializers.CharField(source='pharmacie.nom', read_only=True)
    customer_name = serializers.CharField(
        source='customer.get_full_name',
        read_only=True
    )
    alert_type_display = serializers.CharField(
        source='get_alert_type_display',
        read_only=True
    )
    severity_display = serializers.CharField(
        source='get_severity_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    
    class Meta:
        model = FraudAlert
        fields = [
            'id', 'pharmacie', 'pharmacie_name', 'alert_type',
            'alert_type_display', 'severity', 'severity_display',
            'status', 'status_display', 'customer', 'customer_name',
            'sale', 'prescription', 'product', 'description',
            'indicators', 'risk_score', 'investigated_by',
            'investigation_notes', 'resolution_notes', 'actions_taken',
            'created_at', 'resolved_at'
        ]
        read_only_fields = ['id', 'created_at']


class PurchaseAnomalyLogSerializer(serializers.ModelSerializer):
    """Serializer pour les anomalies d'achat"""
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    
    class Meta:
        model = PurchaseAnomalyLog
        fields = [
            'id', 'customer', 'customer_name', 'sale', 'anomaly_type',
            'description', 'anomaly_score', 'details', 'auto_flagged',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']