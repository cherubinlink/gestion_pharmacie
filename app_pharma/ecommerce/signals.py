"""
Signals pour E-commerce Pharmacie
Automations et logique métier
Application 9
"""
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.db.models import F
from decimal import Decimal
import uuid

from .models import (
    OnlineStore, OnlineProduct, ProductReview, Cart, CartItem,
    OnlineOrder, OnlineOrderItem, OrderStatusHistory,
    PromoCode, PromoCodeUsage, Wishlist, WishlistItem,
    CustomerNotification
)


# ============================================================================
# SIGNALS NUMÉROTATION AUTOMATIQUE
# ============================================================================

@receiver(pre_save, sender=OnlineOrder)
def generate_order_number(sender, instance, **kwargs):
    """Génère un numéro de commande unique"""
    if not instance.order_number:
        # Format: ORD-ANNÉE-NNNNNN
        year = timezone.now().year
        last_order = OnlineOrder.objects.filter(
            order_number__startswith=f'ORD-{year}-'
        ).order_by('-order_number').first()
        
        if last_order:
            last_number = int(last_order.order_number.split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1
        
        instance.order_number = f'ORD-{year}-{new_number:06d}'


# ============================================================================
# SIGNALS CRÉATION AUTOMATIQUE PANIER ET WISHLIST
# ============================================================================

@receiver(post_save, sender='gestion_rh.Client')
def create_cart_and_wishlist_for_new_client(sender, instance, created, **kwargs):
    """Crée automatiquement un panier et une liste de souhaits pour chaque nouveau client"""
    if created:
        # Récupérer la boutique en ligne de la pharmacie du client
        try:
            from .models import OnlineStore
            store = OnlineStore.objects.filter(
                pharmacie=instance.pharmacie,
                is_active=True
            ).first()
            
            if store:
                # Créer le panier
                Cart.objects.get_or_create(
                    store=store,
                    customer=instance,
                    defaults={'is_active': True}
                )
        except Exception as e:
            pass
        
        # Créer la liste de souhaits
        try:
            Wishlist.objects.get_or_create(customer=instance)
        except Exception as e:
            pass


# ============================================================================
# SIGNALS GESTION STOCK
# ============================================================================

@receiver(post_save, sender=OnlineOrder)
def manage_stock_on_order_confirmation(sender, instance, created, **kwargs):
    """Décrémente le stock en ligne lors de la confirmation de commande"""
    if not created:
        # Si la commande vient d'être confirmée
        if instance.status == 'confirmed' and instance.confirmed_at:
            for item in instance.items.all():
                online_product = item.online_product
                # Décrémenter le stock en ligne
                if online_product.online_stock_quantity >= item.quantity:
                    online_product.online_stock_quantity = F('online_stock_quantity') - item.quantity
                    online_product.save(update_fields=['online_stock_quantity'])


@receiver(post_save, sender=OnlineOrder)
def restore_stock_on_order_cancellation(sender, instance, created, **kwargs):
    """Restaure le stock en ligne lors de l'annulation de commande"""
    if not created:
        # Si la commande vient d'être annulée
        if instance.status == 'cancelled' and instance.cancelled_at:
            for item in instance.items.all():
                online_product = item.online_product
                # Restaurer le stock en ligne
                online_product.online_stock_quantity = F('online_stock_quantity') + item.quantity
                online_product.save(update_fields=['online_stock_quantity'])


# ============================================================================
# SIGNALS STATISTIQUES PRODUITS
# ============================================================================

@receiver(post_save, sender=OnlineOrder)
def update_product_sales_count(sender, instance, created, **kwargs):
    """Met à jour le compteur de ventes des produits lors de la livraison"""
    if not created:
        # Si la commande vient d'être livrée
        if instance.status == 'delivered' and instance.delivered_at:
            for item in instance.items.all():
                online_product = item.online_product
                # Incrémenter le compteur de ventes
                online_product.sales_count = F('sales_count') + item.quantity
                online_product.save(update_fields=['sales_count'])


# ============================================================================
# SIGNALS HISTORIQUE STATUT COMMANDE
# ============================================================================

@receiver(post_save, sender=OnlineOrder)
def create_order_status_history(sender, instance, created, **kwargs):
    """Crée un historique à chaque changement de statut"""
    if created:
        # Première entrée pour le statut initial
        OrderStatusHistory.objects.create(
            order=instance,
            status=instance.status,
            comment="Commande créée"
        )
    else:
        # Vérifier si le statut a changé
        old_instance = OnlineOrder.objects.filter(pk=instance.pk).first()
        if old_instance and old_instance.status != instance.status:
            OrderStatusHistory.objects.create(
                order=instance,
                status=instance.status,
                changed_by=instance.confirmed_by,  # ou l'utilisateur qui a fait le changement
                comment=f"Statut changé de {old_instance.status} à {instance.status}"
            )


# ============================================================================
# SIGNALS CRÉATION VENTE PHYSIQUE
# ============================================================================

@receiver(post_save, sender=OnlineOrder)
def create_sale_on_payment(sender, instance, created, **kwargs):
    """Crée une vente dans gestion_vente après paiement confirmé"""
    if not created:
        # Si le paiement vient d'être confirmé et qu'aucune vente n'existe
        if instance.payment_status == 'paid' and instance.paid_at and not instance.sale:
            try:
                from gestion_vente.models import Sale, SaleItem
                
                # Créer la vente
                sale = Sale.objects.create(
                    pharmacie=instance.store.pharmacie,
                    customer=instance.customer,
                    sale_type='retail',
                    payment_method='cash' if instance.payment_method == 'cod' else 'mobile_money',
                    subtotal=instance.subtotal,
                    total=instance.total,
                    amount_paid=instance.total,
                    change_amount=Decimal('0.00'),
                    status='completed',
                    notes=f"Commande en ligne: {instance.order_number}"
                )
                
                # Créer les lignes de vente
                for order_item in instance.items.all():
                    SaleItem.objects.create(
                        sale=sale,
                        product=order_item.online_product.product,
                        quantity=order_item.quantity,
                        unit_price=order_item.unit_price,
                        discount_amount=Decimal('0.00'),
                        subtotal=order_item.subtotal
                    )
                
                # Lier la vente à la commande
                instance.sale = sale
                instance.save(update_fields=['sale'])
                
            except Exception as e:
                # Log l'erreur mais ne bloque pas le processus
                print(f"Erreur création vente: {e}")


# ============================================================================
# SIGNALS CODES PROMO
# ============================================================================

@receiver(post_save, sender=PromoCodeUsage)
def increment_promo_code_usage(sender, instance, created, **kwargs):
    """Incrémente le compteur d'utilisation du code promo"""
    if created:
        promo_code = instance.promo_code
        promo_code.times_used = F('times_used') + 1
        promo_code.save(update_fields=['times_used'])


# ============================================================================
# SIGNALS NOTIFICATIONS CLIENTS
# ============================================================================

@receiver(post_save, sender=OnlineOrder)
def send_order_notifications(sender, instance, created, **kwargs):
    """Envoie des notifications au client selon le statut de la commande"""
    
    notifications_config = {
        'confirmed': {
            'type': 'order_confirmed',
            'title': 'Commande confirmée ✅',
            'message': f'Votre commande {instance.order_number} a été confirmée et est en cours de préparation.'
        },
        'shipped': {
            'type': 'order_shipped',
            'title': 'Commande expédiée 🚚',
            'message': f'Votre commande {instance.order_number} a été expédiée et est en route vers vous.'
        },
        'delivered': {
            'type': 'order_delivered',
            'title': 'Commande livrée 🎉',
            'message': f'Votre commande {instance.order_number} a été livrée avec succès. Merci pour votre confiance !'
        },
        'cancelled': {
            'type': 'order_cancelled',
            'title': 'Commande annulée ❌',
            'message': f'Votre commande {instance.order_number} a été annulée. Raison: {instance.cancellation_reason or "Non spécifiée"}'
        }
    }
    
    if not created and instance.status in notifications_config:
        config = notifications_config[instance.status]
        
        # Créer la notification
        CustomerNotification.objects.create(
            customer=instance.customer,
            notification_type=config['type'],
            title=config['title'],
            message=config['message'],
            order=instance,
            sent_via_email=True,
            sent_via_sms=True,
            sent_via_push=True
        )


# ============================================================================
# SIGNALS AVIS PRODUITS
# ============================================================================

@receiver(post_save, sender=ProductReview)
def verify_purchase_for_review(sender, instance, created, **kwargs):
    """Vérifie si l'avis provient d'un achat vérifié"""
    if created:
        # Vérifier si le client a acheté ce produit
        has_purchased = OnlineOrderItem.objects.filter(
            order__customer=instance.customer,
            order__status='delivered',
            online_product=instance.online_product
        ).exists()
        
        if has_purchased and not instance.verified_purchase:
            instance.verified_purchase = True
            instance.save(update_fields=['verified_purchase'])


# ============================================================================
# SIGNALS LISTE DE SOUHAITS - NOTIFICATIONS
# ============================================================================

@receiver(post_save, sender=OnlineProduct)
def notify_wishlist_price_drop(sender, instance, created, **kwargs):
    """Notifie les clients en liste de souhaits lors d'une baisse de prix"""
    if not created:
        # Vérifier si le prix a baissé
        old_instance = OnlineProduct.objects.filter(pk=instance.pk).first()
        if old_instance:
            old_price = old_instance.get_current_price()
            new_price = instance.get_current_price()
            
            if new_price < old_price:
                # Récupérer les clients qui ont ce produit en wishlist avec notification activée
                wishlist_items = WishlistItem.objects.filter(
                    online_product=instance,
                    notify_on_price_drop=True
                )
                
                for item in wishlist_items:
                    discount_percentage = ((old_price - new_price) / old_price) * 100
                    CustomerNotification.objects.create(
                        customer=item.wishlist.customer,
                        notification_type='price_drop',
                        title=f'Baisse de prix ! 💰',
                        message=f'{instance.product.name} est maintenant à {new_price:,.0f} XAF (-{discount_percentage:.0f}%)',
                        online_product=instance,
                        sent_via_email=True,
                        sent_via_push=True
                    )


@receiver(post_save, sender=OnlineProduct)
def notify_wishlist_back_in_stock(sender, instance, created, **kwargs):
    """Notifie les clients en liste de souhaits quand un produit est de retour en stock"""
    if not created:
        # Vérifier si le stock vient de passer de 0 à > 0
        old_instance = OnlineProduct.objects.filter(pk=instance.pk).first()
        if old_instance and old_instance.online_stock_quantity == 0 and instance.online_stock_quantity > 0:
            # Récupérer les clients qui ont ce produit en wishlist avec notification activée
            wishlist_items = WishlistItem.objects.filter(
                online_product=instance,
                notify_on_availability=True
            )
            
            for item in wishlist_items:
                CustomerNotification.objects.create(
                    customer=item.wishlist.customer,
                    notification_type='back_in_stock',
                    title=f'De retour en stock ! 🎉',
                    message=f'{instance.product.name} est maintenant disponible à {instance.get_current_price():,.0f} XAF',
                    online_product=instance,
                    sent_via_email=True,
                    sent_via_push=True
                )


# ============================================================================
# SIGNALS PANIERS ABANDONNÉS
# ============================================================================

@receiver(post_save, sender=Cart)
def detect_abandoned_cart(sender, instance, created, **kwargs):
    """Marque un panier comme abandonné après 24h d'inactivité"""
    if not created:
        # Vérifier si le panier est actif et n'a pas été mis à jour depuis 24h
        if instance.is_active and instance.items.exists():
            time_since_update = timezone.now() - instance.updated_at
            if time_since_update.total_seconds() >= 86400:  # 24 heures
                # Marquer comme abandonné
                if not instance.abandoned_at:
                    instance.abandoned_at = timezone.now()
                    instance.save(update_fields=['abandoned_at'])
                    
                    # Créer une notification
                    CustomerNotification.objects.create(
                        customer=instance.customer,
                        notification_type='abandoned_cart',
                        title='Vous avez oublié quelque chose ? 🛒',
                        message=f'Votre panier contient {instance.get_total_items()} article(s) pour {instance.get_total():,.0f} XAF. Finalisez votre commande maintenant !',
                        sent_via_email=True,
                        sent_via_push=True
                    )


@receiver(post_save, sender=CartItem)
def reset_cart_abandoned_status(sender, instance, created, **kwargs):
    """Réinitialise le statut abandonné quand le panier est modifié"""
    cart = instance.cart
    if cart.abandoned_at:
        cart.abandoned_at = None
        cart.save(update_fields=['abandoned_at'])


# ============================================================================
# SIGNALS CALCULS AUTOMATIQUES COMMANDE
# ============================================================================

@receiver(pre_save, sender=OnlineOrder)
def calculate_order_totals(sender, instance, **kwargs):
    """Calcule automatiquement les totaux de la commande"""
    # Le calcul du total sera fait après la création des items
    # Mais on peut initialiser ici
    if not instance.pk:
        instance.total = instance.subtotal + instance.delivery_fee - instance.discount_amount


@receiver(post_save, sender=OnlineOrderItem)
def update_order_totals_on_item_change(sender, instance, created, **kwargs):
    """Met à jour les totaux de la commande quand un item change"""
    order = instance.order
    
    # Recalculer le sous-total
    subtotal = sum(item.subtotal for item in order.items.all())
    order.subtotal = subtotal
    
    # Recalculer les frais de livraison (livraison gratuite si seuil atteint)
    if order.delivery_method == 'delivery':
        if subtotal >= order.store.free_delivery_threshold:
            order.delivery_fee = Decimal('0.00')
        else:
            order.delivery_fee = order.store.delivery_fee
    else:
        order.delivery_fee = Decimal('0.00')
    
    # Recalculer le total
    order.total = order.subtotal + order.delivery_fee - order.discount_amount
    
    order.save(update_fields=['subtotal', 'delivery_fee', 'total'])


# ============================================================================
# SIGNALS VALIDATION CODE PROMO
# ============================================================================

@receiver(pre_save, sender=OnlineOrder)
def validate_and_apply_promo_code(sender, instance, **kwargs):
    """Valide et applique le code promo à la commande"""
    if instance.promo_code and not instance.pk:
        promo_code = instance.promo_code
        
        # Vérifier si le code est valide
        if promo_code.is_valid():
            # Vérifier limite par client
            usage_count = PromoCodeUsage.objects.filter(
                promo_code=promo_code,
                customer=instance.customer
            ).count()
            
            if usage_count < promo_code.usage_limit_per_customer:
                # Appliquer la réduction
                discount = promo_code.calculate_discount(instance.subtotal)
                instance.discount_amount = discount
                
                # Si c'est une livraison gratuite
                if promo_code.discount_type == 'free_delivery':
                    instance.delivery_fee = Decimal('0.00')


# ============================================================================
# SIGNALS NETTOYAGE
# ============================================================================

@receiver(post_delete, sender=OnlineProduct)
def cleanup_product_images(sender, instance, **kwargs):
    """Supprime les images du produit lors de sa suppression"""
    # Supprimer l'image principale
    if instance.primary_image:
        instance.primary_image.delete(save=False)
    
    # Les images supplémentaires seront supprimées via CASCADE


@receiver(post_delete, sender=OnlineOrder)
def cleanup_order_prescription(sender, instance, **kwargs):
    """Supprime le fichier d'ordonnance lors de la suppression de la commande"""
    if instance.prescription_file:
        instance.prescription_file.delete(save=False)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def send_email_notification(customer, subject, message):
    """Helper pour envoyer des emails (à implémenter avec votre service d'email)"""
    # TODO: Implémenter avec Django email ou service externe
    pass


def send_sms_notification(customer, message):
    """Helper pour envoyer des SMS (à implémenter avec votre service SMS)"""
    # TODO: Implémenter avec service SMS
    pass


def send_push_notification(customer, title, message):
    """Helper pour envoyer des notifications push (à implémenter)"""
    # TODO: Implémenter avec service push notifications
    pass