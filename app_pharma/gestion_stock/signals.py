"""
Signals Django pour automatiser la gestion de stock
Automatisations : alertes, réapprovisionnement, mouvements, prévisions
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.db.models import Sum, F, Q, Count
from datetime import timedelta
from decimal import Decimal

from gestion_stock.models import (
    Supplier, Batch, StockItem, PurchaseOrder, PurchaseOrderItem,
    Reception, ReceptionItem, Inventory, InventoryCount,
    StockMovement, StockAlert, ReorderRule, StockForecast
)


# ============================================================================
# SIGNALS NUMÉROTATION AUTOMATIQUE
# ============================================================================

@receiver(pre_save, sender=Supplier)
def generate_supplier_code(sender, instance, **kwargs):
    """Génère automatiquement un code fournisseur"""
    if not instance.supplier_code:
        count = Supplier.objects.filter(pharmacie=instance.pharmacie).count() + 1
        instance.supplier_code = f"FOUR-{instance.pharmacie.code if hasattr(instance.pharmacie, 'code') else 'PH'}-{count:05d}"


@receiver(pre_save, sender=PurchaseOrder)
def generate_purchase_order_number(sender, instance, **kwargs):
    """Génère automatiquement un numéro de commande"""
    if not instance.order_number:
        year = timezone.now().year
        count = PurchaseOrder.objects.filter(
            pharmacie=instance.pharmacie,
            order_date__year=year
        ).count() + 1
        instance.order_number = f"CMD-{year}-{count:06d}"


@receiver(pre_save, sender=Reception)
def generate_reception_number(sender, instance, **kwargs):
    """Génère automatiquement un numéro de réception"""
    if not instance.reception_number:
        year = timezone.now().year
        count = Reception.objects.filter(
            pharmacie=instance.pharmacie,
            reception_date__year=year
        ).count() + 1
        instance.reception_number = f"REC-{year}-{count:06d}"


@receiver(pre_save, sender=Inventory)
def generate_inventory_number(sender, instance, **kwargs):
    """Génère automatiquement un numéro d'inventaire"""
    if not instance.inventory_number:
        year = instance.scheduled_date.year
        count = Inventory.objects.filter(
            pharmacie=instance.pharmacie,
            scheduled_date__year=year
        ).count() + 1
        instance.inventory_number = f"INV-{year}-{count:05d}"


@receiver(pre_save, sender=StockMovement)
def generate_movement_number(sender, instance, **kwargs):
    """Génère automatiquement un numéro de mouvement"""
    if not instance.movement_number:
        date = timezone.now()
        count = StockMovement.objects.filter(
            pharmacie=instance.pharmacie,
            movement_date__date=date.date()
        ).count() + 1
        instance.movement_number = f"MVT-{date.strftime('%Y%m%d')}-{count:04d}"


# ============================================================================
# SIGNALS ALERTES DE STOCK
# ============================================================================

@receiver(post_save, sender=StockItem)
def check_stock_levels(sender, instance, **kwargs):
    """Vérifie les niveaux de stock et crée des alertes"""
    product = instance.product
    total_stock = StockItem.objects.filter(product=product).aggregate(
        total=Sum('quantity')
    )['total'] or 0
    
    # Alerte stock faible
    if total_stock <= product.min_stock_level and total_stock > 0:
        StockAlert.objects.get_or_create(
            pharmacie=product.pharmacie,
            product=product,
            alert_type='low_stock',
            status='active',
            defaults={
                'severity': 'high',
                'message': f'Stock faible pour {product.name}: {total_stock} unité(s)',
                'current_stock': total_stock,
                'threshold_value': product.min_stock_level
            }
        )
    
    # Alerte rupture
    if total_stock == 0:
        StockAlert.objects.get_or_create(
            pharmacie=product.pharmacie,
            product=product,
            alert_type='out_of_stock',
            status='active',
            defaults={
                'severity': 'critical',
                'message': f'Rupture de stock: {product.name}',
                'current_stock': 0,
                'threshold_value': product.min_stock_level
            }
        )


@receiver(post_save, sender=Batch)
def check_expiry_dates(sender, instance, created, **kwargs):
    """Vérifie les dates de péremption et crée des alertes"""
    days_until_expiry = instance.days_until_expiry()
    
    # Alerte produit expiré
    if instance.is_expired() and instance.current_quantity > 0:
        StockAlert.objects.get_or_create(
            pharmacie=instance.product.pharmacie,
            product=instance.product,
            batch=instance,
            alert_type='expired',
            status='active',
            defaults={
                'severity': 'critical',
                'message': f'Lot expiré: {instance.batch_number} ({instance.product.name})',
                'current_stock': instance.current_quantity
            }
        )
    
    # Alerte expiration proche (30 jours)
    elif 0 < days_until_expiry <= 30 and instance.current_quantity > 0:
        severity = 'critical' if days_until_expiry <= 7 else 'high'
        StockAlert.objects.get_or_create(
            pharmacie=instance.product.pharmacie,
            product=instance.product,
            batch=instance,
            alert_type='expiring_soon',
            status='active',
            defaults={
                'severity': severity,
                'message': f'Expiration dans {days_until_expiry} jours: {instance.batch_number}',
                'current_stock': instance.current_quantity
            }
        )


# ============================================================================
# SIGNALS RÉAPPROVISIONNEMENT AUTOMATIQUE
# ============================================================================

@receiver(post_save, sender=StockItem)
def trigger_auto_reorder(sender, instance, **kwargs):
    """Déclenche le réapprovisionnement automatique si nécessaire"""
    try:
        reorder_rule = instance.product.reorder_rule
        if not reorder_rule.is_active or not reorder_rule.auto_create_order:
            return
        
        total_stock = StockItem.objects.filter(
            product=instance.product
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        if reorder_rule.should_reorder(total_stock):
            # Vérifier si une commande n'a pas déjà été créée récemment
            recent_order = PurchaseOrder.objects.filter(
                items__product=instance.product,
                status__in=['draft', 'sent', 'confirmed'],
                order_date__gte=timezone.now().date() - timedelta(days=7)
            ).exists()
            
            if not recent_order:
                # Créer une commande automatique
                supplier = reorder_rule.preferred_supplier
                if supplier:
                    order = PurchaseOrder.objects.create(
                        pharmacie=instance.product.pharmacie,
                        supplier=supplier,
                        status='draft',
                        is_auto_generated=True,
                        notes=f'Commande générée automatiquement - Stock sous le seuil'
                    )
                    
                    PurchaseOrderItem.objects.create(
                        purchase_order=order,
                        product=instance.product,
                        quantity_ordered=reorder_rule.reorder_quantity,
                        unit_price=instance.product.purchase_price
                    )
                    
                    # Créer une alerte
                    StockAlert.objects.create(
                        pharmacie=instance.product.pharmacie,
                        product=instance.product,
                        alert_type='reorder_needed',
                        severity='normal',
                        status='active',
                        message=f'Commande auto créée: {order.order_number}',
                        current_stock=total_stock
                    )
                    
                    reorder_rule.last_auto_order_date = timezone.now().date()
                    reorder_rule.save()
    
    except ReorderRule.DoesNotExist:
        pass


# ============================================================================
# SIGNALS COMMANDES ET RÉCEPTIONS
# ============================================================================

@receiver(post_save, sender=PurchaseOrderItem)
def update_purchase_order_totals(sender, instance, **kwargs):
    """Met à jour les totaux de la commande"""
    order = instance.purchase_order
    totals = order.calculate_totals()
    
    PurchaseOrder.objects.filter(pk=order.pk).update(
        subtotal=totals['subtotal'],
        tax_amount=totals['tax_amount'],
        total_amount=totals['total_amount']
    )


@receiver(post_save, sender=ReceptionItem)
def create_batch_and_stock_on_reception(sender, instance, created, **kwargs):
    """Crée automatiquement le lot et met à jour le stock lors de la réception"""
    if instance.quantity_accepted > 0 and instance.is_conform:
        product = instance.purchase_order_item.product
        
        # Créer ou mettre à jour le lot
        batch, batch_created = Batch.objects.get_or_create(
            product=product,
            batch_number=instance.batch_number,
            defaults={
                'expiry_date': instance.expiry_date,
                'initial_quantity': instance.quantity_accepted,
                'current_quantity': instance.quantity_accepted,
                'supplier': instance.reception.purchase_order.supplier,
                'purchase_order': instance.reception.purchase_order,
                'unit_cost': instance.purchase_order_item.unit_price,
                'status': 'in_stock'
            }
        )
        
        if not batch_created:
            batch.current_quantity += instance.quantity_accepted
            batch.save()
        
        # Créer un mouvement de stock
        StockMovement.objects.create(
            pharmacie=product.pharmacie,
            movement_type='purchase',
            product=product,
            batch=batch,
            quantity=instance.quantity_accepted,
            purchase_order=instance.reception.purchase_order,
            performed_by=instance.reception.received_by,
            reason=f'Réception {instance.reception.reception_number}'
        )
        
        # Mettre à jour la quantité reçue dans la commande
        poi = instance.purchase_order_item
        poi.quantity_received = F('quantity_received') + instance.quantity_accepted
        poi.save()


@receiver(post_save, sender=Reception)
def update_purchase_order_status(sender, instance, **kwargs):
    """Met à jour le statut de la commande après réception"""
    if instance.status == 'completed':
        order = instance.purchase_order
        total_ordered = order.items.aggregate(total=Sum('quantity_ordered'))['total'] or 0
        total_received = order.items.aggregate(total=Sum('quantity_received'))['total'] or 0
        
        if total_received >= total_ordered:
            order.status = 'received'
            order.actual_delivery_date = instance.reception_date
        elif total_received > 0:
            order.status = 'partially_received'
        
        order.save()


# ============================================================================
# SIGNALS INVENTAIRE
# ============================================================================

@receiver(post_save, sender=InventoryCount)
def apply_inventory_adjustments(sender, instance, created, **kwargs):
    """Applique les ajustements d'inventaire au stock"""
    if instance.is_verified and instance.discrepancy != 0:
        # Créer un mouvement de stock pour ajustement
        StockMovement.objects.create(
            pharmacie=instance.inventory.pharmacie,
            movement_type='adjustment',
            product=instance.product,
            batch=instance.batch,
            quantity=abs(instance.discrepancy),
            reason=f'Ajustement inventaire {instance.inventory.inventory_number}',
            notes=f'Écart: {instance.discrepancy}. {instance.notes}',
            performed_by=instance.verified_by
        )
        
        # Mettre à jour le stock
        if instance.batch:
            instance.batch.current_quantity = instance.counted_quantity
            instance.batch.save()


@receiver(post_save, sender=InventoryCount)
def update_inventory_statistics(sender, instance, **kwargs):
    """Met à jour les statistiques de l'inventaire"""
    inventory = instance.inventory
    
    stats = inventory.counts.aggregate(
        total_items=Count('id'),
        total_discrepancies=Count('id', filter=Q(discrepancy__ne=0)),
        value_discrepancy=Sum('discrepancy_value')
    )
    
    Inventory.objects.filter(pk=inventory.pk).update(
        total_items_counted=stats['total_items'] or 0,
        total_discrepancies=stats['total_discrepancies'] or 0,
        value_discrepancy=stats['value_discrepancy'] or Decimal('0.00')
    )


# ============================================================================
# SIGNALS PERFORMANCE FOURNISSEURS
# ============================================================================

@receiver(post_save, sender=Reception)
def update_supplier_performance(sender, instance, **kwargs):
    """Met à jour les indicateurs de performance du fournisseur"""
    if instance.status == 'completed':
        supplier = instance.purchase_order.supplier
        order = instance.purchase_order
        
        # Incrémenter le nombre de commandes
        supplier.total_orders = F('total_orders') + 1
        
        # Calculer le taux de livraison à temps
        if order.expected_delivery_date:
            on_time = instance.reception_date <= order.expected_delivery_date
            
            # Recalculer le taux
            completed_orders = PurchaseOrder.objects.filter(
                supplier=supplier,
                status__in=['received', 'closed']
            ).count()
            
            on_time_orders = PurchaseOrder.objects.filter(
                supplier=supplier,
                status__in=['received', 'closed'],
                actual_delivery_date__lte=F('expected_delivery_date')
            ).count()
            
            if completed_orders > 0:
                supplier.on_time_delivery_rate = (on_time_orders / completed_orders) * 100
        
        # Calculer le taux de qualité
        if not instance.has_discrepancies and not instance.has_damages:
            # Bonne qualité
            pass
        
        supplier.save()


# ============================================================================
# HELPER FUNCTIONS POUR PRÉVISIONS IA
# ============================================================================

def calculate_demand_forecast(product, forecast_date, forecast_type='weekly'):
    """
    Calcule les prévisions de demande pour un produit
    (Simplifié - à remplacer par un vrai modèle ML)
    """
    from gestion_vente.models import SaleItem
    from django.db.models import Sum, Avg
    
    # Période de référence
    if forecast_type == 'daily':
        days_back = 30
    elif forecast_type == 'weekly':
        days_back = 90
    else:  # monthly
        days_back = 365
    
    start_date = forecast_date - timedelta(days=days_back)
    
    # Calculer la demande moyenne
    avg_demand = SaleItem.objects.filter(
        product=product,
        sale__sale_date__gte=start_date,
        sale__status='completed'
    ).aggregate(avg=Avg('quantity'))['avg'] or 0
    
    # Facteur saisonnier simplifié (à améliorer avec ML)
    month = forecast_date.month
    seasonal_factors = {
        12: 1.2, 1: 1.1, 2: 0.9,  # Hiver
        3: 1.0, 4: 1.0, 5: 1.0,    # Printemps
        6: 0.8, 7: 0.7, 8: 0.8,    # Été
        9: 1.0, 10: 1.1, 11: 1.2   # Automne
    }
    seasonal_factor = seasonal_factors.get(month, 1.0)
    
    predicted_demand = int(avg_demand * seasonal_factor)
    
    return {
        'predicted_demand': predicted_demand,
        'seasonal_factor': Decimal(str(seasonal_factor)),
        'confidence_level': Decimal('75.00'),  # À calculer avec ML
        'training_points': days_back
    }
