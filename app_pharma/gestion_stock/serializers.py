"""
Serializers DRF pour la gestion de stock
"""
from rest_framework import serializers
from decimal import Decimal
from .models import (
    # Fournisseurs et Stock
    Supplier, StorageLocation, Batch, StockItem, StockMovement,
    # Commandes
    PurchaseOrder, PurchaseOrderItem, Reception, ReceptionItem,
    # Inventaires
    Inventory, InventoryCount,
    # IA et Prévisions
    StockForecast, ReorderRule, StockAlert
)



# ============================================================================
# SERIALIZERS FOURNISSEURS
# ============================================================================

class SupplierSerializer(serializers.ModelSerializer):
    """Serializer pour les fournisseurs"""
    pharmacie_name = serializers.CharField(source='pharmacie.nom', read_only=True)
    performance_score = serializers.SerializerMethodField()
    total_orders_count = serializers.IntegerField(source='total_orders', read_only=True)
    
    class Meta:
        model = Supplier
        fields = [
            'id', 'pharmacie', 'pharmacie_name', 'supplier_code', 'name',
            'supplier_type', 'contact_person', 'email', 'phone', 'mobile',
            'fax', 'website', 'address', 'city', 'country', 'postal_code',
            'tax_id', 'registration_number', 'payment_terms',
            'min_order_amount', 'delivery_time', 'rating',
            'total_orders_count', 'on_time_delivery_rate', 'quality_rate',
            'performance_score', 'status', 'is_preferred', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'supplier_code', 'total_orders', 'created_at', 'updated_at']
    
    def get_performance_score(self, obj):
        return obj.calculate_performance_score()


class SupplierListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour la liste de fournisseurs"""
    performance_score = serializers.SerializerMethodField()
    
    class Meta:
        model = Supplier
        fields = [
            'id', 'supplier_code', 'name', 'supplier_type', 'email',
            'phone', 'rating', 'performance_score', 'status', 'is_preferred'
        ]
    
    def get_performance_score(self, obj):
        return obj.calculate_performance_score()


# ============================================================================
# SERIALIZERS STOCK
# ============================================================================

class StorageLocationSerializer(serializers.ModelSerializer):
    """Serializer pour les emplacements"""
    pharmacie_name = serializers.CharField(source='pharmacie.nom', read_only=True)
    occupancy_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = StorageLocation
        fields = [
            'id', 'pharmacie', 'pharmacie_name', 'location_code', 'name',
            'location_type', 'parent_location', 'capacity',
            'temperature_min', 'temperature_max', 'occupancy_rate',
            'is_active', 'description', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_occupancy_rate(self, obj):
        return obj.get_current_occupancy()


class BatchSerializer(serializers.ModelSerializer):
    """Serializer pour les lots"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    is_expired = serializers.SerializerMethodField()
    days_until_expiry = serializers.SerializerMethodField()
    available_quantity = serializers.SerializerMethodField()
    
    class Meta:
        model = Batch
        fields = [
            'id', 'product', 'product_name', 'product_sku', 'batch_number',
            'manufacturing_date', 'expiry_date', 'initial_quantity',
            'current_quantity', 'reserved_quantity', 'available_quantity',
            'supplier', 'supplier_name', 'purchase_order', 'unit_cost',
            'status', 'is_expired', 'days_until_expiry', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_is_expired(self, obj):
        return obj.is_expired()
    
    def get_days_until_expiry(self, obj):
        return obj.days_until_expiry()
    
    def get_available_quantity(self, obj):
        return obj.available_quantity()


class StockItemSerializer(serializers.ModelSerializer):
    """Serializer pour les items de stock"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    batch_number = serializers.CharField(source='batch.batch_number', read_only=True)
    location_name = serializers.CharField(source='storage_location.name', read_only=True)
    expiry_date = serializers.DateField(source='batch.expiry_date', read_only=True)
    
    class Meta:
        model = StockItem
        fields = [
            'id', 'product', 'product_name', 'batch', 'batch_number',
            'storage_location', 'location_name', 'quantity',
            'expiry_date', 'last_counted_at', 'last_counted_by',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class StockMovementSerializer(serializers.ModelSerializer):
    """Serializer pour les mouvements de stock"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    from_location_name = serializers.CharField(
        source='from_location.name',
        read_only=True
    )
    to_location_name = serializers.CharField(
        source='to_location.name',
        read_only=True
    )
    performed_by_name = serializers.CharField(
        source='performed_by.get_full_name',
        read_only=True
    )
    
    class Meta:
        model = StockMovement
        fields = [
            'id', 'pharmacie', 'movement_number', 'movement_type',
            'product', 'product_name', 'batch', 'from_location',
            'from_location_name', 'to_location', 'to_location_name',
            'quantity', 'purchase_order', 'sale', 'reason', 'notes',
            'performed_by', 'performed_by_name', 'movement_date',
            'created_at'
        ]
        read_only_fields = ['id', 'movement_number', 'created_at']


# ============================================================================
# SERIALIZERS COMMANDES
# ============================================================================

class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    """Serializer pour les lignes de commande"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    
    class Meta:
        model = PurchaseOrderItem
        fields = [
            'id', 'purchase_order', 'product', 'product_name', 'product_sku',
            'quantity_ordered', 'quantity_received', 'unit_price',
            'discount_percentage', 'line_subtotal', 'tax_amount',
            'line_total', 'notes', 'created_at'
        ]
        read_only_fields = [
            'id', 'line_subtotal', 'tax_amount', 'line_total', 'created_at'
        ]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    """Serializer pour les commandes fournisseurs"""
    items = PurchaseOrderItemSerializer(many=True, read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    pharmacie_name = serializers.CharField(source='pharmacie.nom', read_only=True)
    created_by_name = serializers.CharField(
        source='created_by.get_full_name',
        read_only=True
    )
    is_overdue = serializers.SerializerMethodField()
    
    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'pharmacie', 'pharmacie_name', 'order_number', 'supplier',
            'supplier_name', 'order_date', 'expected_delivery_date',
            'actual_delivery_date', 'status', 'priority', 'subtotal',
            'tax_amount', 'shipping_cost', 'discount_amount', 'total_amount',
            'delivery_address', 'shipping_method', 'tracking_number',
            'pdf_file', 'is_auto_generated', 'notes', 'internal_notes',
            'sent_at', 'sent_by', 'sent_method', 'created_by',
            'created_by_name', 'approved_by', 'approved_at', 'is_overdue',
            'items', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'order_number', 'subtotal', 'tax_amount', 'total_amount',
            'created_at', 'updated_at'
        ]
    
    def get_is_overdue(self, obj):
        return obj.is_overdue()


class PurchaseOrderListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour liste de commandes"""
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'order_number', 'supplier_name', 'order_date',
            'expected_delivery_date', 'status', 'priority',
            'total_amount', 'items_count'
        ]
    
    def get_items_count(self, obj):
        return obj.items.count()


class ReceptionItemSerializer(serializers.ModelSerializer):
    """Serializer pour les lignes de réception"""
    product_name = serializers.CharField(
        source='purchase_order_item.product.name',
        read_only=True
    )
    has_discrepancy = serializers.SerializerMethodField()
    
    class Meta:
        model = ReceptionItem
        fields = [
            'id', 'reception', 'purchase_order_item', 'product_name',
            'quantity_expected', 'quantity_received', 'quantity_accepted',
            'quantity_rejected', 'batch_number', 'expiry_date',
            'is_conform', 'discrepancy_type', 'has_discrepancy',
            'notes', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_has_discrepancy(self, obj):
        return obj.has_discrepancy()


class ReceptionSerializer(serializers.ModelSerializer):
    """Serializer pour les réceptions"""
    items = ReceptionItemSerializer(many=True, read_only=True)
    order_number = serializers.CharField(
        source='purchase_order.order_number',
        read_only=True
    )
    received_by_name = serializers.CharField(
        source='received_by.get_full_name',
        read_only=True
    )
    
    class Meta:
        model = Reception
        fields = [
            'id', 'pharmacie', 'reception_number', 'purchase_order',
            'order_number', 'reception_date', 'status',
            'delivery_note_number', 'carrier_name', 'is_complete',
            'has_discrepancies', 'has_damages', 'delivery_note_file',
            'notes', 'received_by', 'received_by_name', 'validated_by',
            'validated_at', 'items', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'reception_number', 'created_at', 'updated_at']


# ============================================================================
# SERIALIZERS INVENTAIRES
# ============================================================================

class InventoryCountSerializer(serializers.ModelSerializer):
    """Serializer pour les comptages"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    location_name = serializers.CharField(
        source='storage_location.name',
        read_only=True
    )
    counted_by_name = serializers.CharField(
        source='counted_by.get_full_name',
        read_only=True
    )
    
    class Meta:
        model = InventoryCount
        fields = [
            'id', 'inventory', 'product', 'product_name', 'batch',
            'storage_location', 'location_name', 'expected_quantity',
            'counted_quantity', 'discrepancy', 'unit_cost',
            'discrepancy_value', 'is_verified', 'recount_required',
            'notes', 'counted_by', 'counted_by_name', 'counted_at',
            'verified_by', 'verified_at', 'created_at'
        ]
        read_only_fields = [
            'id', 'discrepancy', 'discrepancy_value', 'created_at'
        ]


class InventorySerializer(serializers.ModelSerializer):
    """Serializer pour les inventaires"""
    counts = InventoryCountSerializer(many=True, read_only=True)
    pharmacie_name = serializers.CharField(source='pharmacie.nom', read_only=True)
    created_by_name = serializers.CharField(
        source='created_by.get_full_name',
        read_only=True
    )
    
    class Meta:
        model = Inventory
        fields = [
            'id', 'pharmacie', 'pharmacie_name', 'inventory_number',
            'inventory_type', 'scheduled_date', 'start_date', 'end_date',
            'status', 'storage_locations', 'product_categories',
            'total_items_counted', 'total_discrepancies',
            'value_discrepancy', 'assigned_to', 'notes', 'created_by',
            'created_by_name', 'validated_by', 'validated_at',
            'counts', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'inventory_number', 'total_items_counted',
            'total_discrepancies', 'value_discrepancy',
            'created_at', 'updated_at'
        ]


# ============================================================================
# SERIALIZERS IA ET PRÉVISIONS
# ============================================================================

class StockForecastSerializer(serializers.ModelSerializer):
    """Serializer pour les prévisions"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    
    class Meta:
        model = StockForecast
        fields = [
            'id', 'product', 'product_name', 'product_sku', 'forecast_date',
            'forecast_type', 'predicted_demand', 'confidence_level',
            'recommended_stock_level', 'recommended_order_quantity',
            'seasonal_factor', 'trend_factor', 'stockout_risk',
            'algorithm_used', 'training_data_points', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ReorderRuleSerializer(serializers.ModelSerializer):
    """Serializer pour les règles de réapprovisionnement"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    preferred_supplier_name = serializers.CharField(
        source='preferred_supplier.name',
        read_only=True
    )
    
    class Meta:
        model = ReorderRule
        fields = [
            'id', 'product', 'product_name', 'reorder_method',
            'reorder_point', 'reorder_quantity', 'max_stock_level',
            'lead_time_days', 'safety_stock', 'preferred_supplier',
            'preferred_supplier_name', 'is_active', 'auto_create_order',
            'last_auto_order_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'last_auto_order_date', 'created_at', 'updated_at']


class StockAlertSerializer(serializers.ModelSerializer):
    """Serializer pour les alertes de stock"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    batch_number = serializers.CharField(source='batch.batch_number', read_only=True)
    acknowledged_by_name = serializers.CharField(
        source='acknowledged_by.get_full_name',
        read_only=True
    )
    
    class Meta:
        model = StockAlert
        fields = [
            'id', 'pharmacie', 'alert_type', 'severity', 'status',
            'product', 'product_name', 'batch', 'batch_number',
            'message', 'current_stock', 'threshold_value',
            'acknowledged_by', 'acknowledged_by_name', 'acknowledged_at',
            'created_at', 'resolved_at'
        ]
        read_only_fields = ['id', 'created_at']