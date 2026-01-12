"""
Signals pour automatiser les processus de vente
"""
from django.db.models.signals import post_save, pre_save, m2m_changed
from django.dispatch import receiver
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q, F
from decimal import Decimal
from datetime import timedelta
import qrcode
from io import BytesIO
from django.core.files import File

from gestion_vente.models import (
    Product, Sale, SaleItem, Payment, ElectronicPrescription,
    ProductPerformance, CustomerPurchasePattern, ProductRecommendation,
    FraudAlert, PurchaseAnomalyLog, SalesAnalytics,CashRegister, CashTransaction, CashCount,
    ChangeShortage, Sale,
)


# ============================================================================
# SIGNALS PRODUITS
# ============================================================================

@receiver(post_save, sender=Product)
def check_low_stock_alert(sender, instance, created, **kwargs):
    """Crée une alerte si le stock est faible"""
    if instance.is_low_stock() and instance.is_active:
        from gestion_communication.models import Notification
        
        # Notifier le gestionnaire de stock
        Notification.objects.create(
            recipient=instance.pharmacie.owner,  # Ou un gestionnaire désigné
            notification_type='stock_low',
            priority='high' if instance.is_out_of_stock() else 'normal',
            title=f'⚠️ Stock faible: {instance.name}',
            message=f'Stock actuel: {instance.stock_quantity} (seuil: {instance.min_stock_level})',
            send_in_app=True,
            send_email=True,
            data={
                'product_id': str(instance.id),
                'current_stock': instance.stock_quantity,
                'min_stock': instance.min_stock_level
            }
        )


# ============================================================================
# SIGNALS VENTES
# ============================================================================

@receiver(pre_save, sender=Sale)
def generate_sale_number(sender, instance, **kwargs):
    """Génère automatiquement un numéro de vente"""
    if not instance.sale_number:
        year = timezone.now().year
        count = Sale.objects.filter(
            pharmacie=instance.pharmacie,
            sale_date__year=year
        ).count() + 1
        
        instance.sale_number = f"VTE-{instance.pharmacie.code if hasattr(instance.pharmacie, 'code') else 'PHARM'}-{year}-{count:06d}"


@receiver(post_save, sender=SaleItem)
def update_sale_totals(sender, instance, created, **kwargs):
    """Met à jour les totaux de la vente après ajout/modification d'un item"""
    if created or instance._state.fields_cache:
        sale = instance.sale
        totals = sale.calculate_totals()
        
        Sale.objects.filter(pk=sale.pk).update(
            subtotal=totals['subtotal'],
            discount_amount=totals['discount_amount'],
            tax_amount=totals['tax_amount'],
            total_amount=totals['total_amount'],
            profit_amount=totals['profit_amount']
        )


@receiver(post_save, sender=SaleItem)
def update_product_stock(sender, instance, created, **kwargs):
    """Diminue le stock du produit lors d'une vente"""
    if created:
        product = instance.product
        product.stock_quantity = F('stock_quantity') - instance.quantity
        product.save(update_fields=['stock_quantity'])
        
        # Recharger pour avoir la valeur actuelle
        product.refresh_from_db()


@receiver(post_save, sender=Sale)
def generate_qr_code_for_ticket(sender, instance, created, **kwargs):
    """Génère un QR code pour le ticket de caisse"""
    if created and not instance.ticket_qr_code:
        # Créer les données du QR code
        qr_data = {
            'sale_number': instance.sale_number,
            'date': instance.sale_date.isoformat(),
            'total': str(instance.total_amount),
            'pharmacie': instance.pharmacie.nom,
            'url': f'https://pharmacie.com/ticket/{instance.id}'  # URL pour consulter les infos
        }
        
        # Générer le QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(str(qr_data))
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Sauvegarder
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        file_name = f'qr_{instance.sale_number}.png'
        instance.ticket_qr_code.save(file_name, File(buffer), save=True)


@receiver(post_save, sender=Sale)
def update_customer_purchase_pattern(sender, instance, created, **kwargs):
    """Met à jour les patterns d'achat du client"""
    if instance.customer and instance.status == 'completed':
        pattern, _ = CustomerPurchasePattern.objects.get_or_create(
            customer=instance.customer,
            pharmacie=instance.pharmacie
        )
        
        # Mettre à jour les statistiques
        completed_sales = Sale.objects.filter(
            customer=instance.customer,
            pharmacie=instance.pharmacie,
            status='completed'
        )
        
        pattern.total_purchases = completed_sales.count()
        pattern.total_spent = completed_sales.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00')
        
        pattern.average_basket_value = (
            pattern.total_spent / pattern.total_purchases
            if pattern.total_purchases > 0 else Decimal('0.00')
        )
        
        pattern.last_purchase_date = instance.sale_date.date()
        
        # Calculer la fréquence d'achat
        if pattern.total_purchases >= 2:
            first_purchase = completed_sales.earliest('sale_date')
            days_span = (instance.sale_date.date() - first_purchase.sale_date.date()).days
            pattern.average_purchase_frequency = days_span // pattern.total_purchases
            
            # Prédire le prochain achat
            pattern.next_predicted_purchase = (
                pattern.last_purchase_date + 
                timedelta(days=pattern.average_purchase_frequency)
            )
        
        pattern.save()


@receiver(post_save, sender=Sale)
def detect_purchase_anomalies(sender, instance, created, **kwargs):
    """Détecte les anomalies dans les achats"""
    if created and instance.customer and instance.status == 'completed':
        anomaly_score = 0
        anomalies = []
        
        # 1. Vérifier les achats multiples le même jour
        today_purchases = Sale.objects.filter(
            customer=instance.customer,
            sale_date__date=instance.sale_date.date(),
            status='completed'
        ).count()
        
        if today_purchases > 3:
            anomaly_score += 20
            anomalies.append('multiple_purchases_same_day')
        
        # 2. Vérifier les montants inhabituels
        avg_basket = CustomerPurchasePattern.objects.filter(
            customer=instance.customer
        ).aggregate(avg=Avg('average_basket_value'))['avg'] or Decimal('0.00')
        
        if avg_basket > 0 and instance.total_amount > avg_basket * 3:
            anomaly_score += 30
            anomalies.append('unusually_high_amount')
        
        # 3. Vérifier les quantités excessives
        for item in instance.items.all():
            if item.quantity > 10:
                anomaly_score += 15
                anomalies.append('excessive_quantity')
                break
        
        # 4. Achats dans plusieurs pharmacies le même jour
        if instance.pharmacie:
            other_pharmacies = Sale.objects.filter(
                customer=instance.customer,
                sale_date__date=instance.sale_date.date(),
                status='completed'
            ).exclude(pharmacie=instance.pharmacie).count()
            
            if other_pharmacies > 0:
                anomaly_score += 25
                anomalies.append('multiple_pharmacies_same_day')
        
        # Créer un log si anomalie détectée
        if anomaly_score >= 20:
            PurchaseAnomalyLog.objects.create(
                customer=instance.customer,
                sale=instance,
                anomaly_type='purchase_pattern',
                description=f"Anomalie détectée: {', '.join(anomalies)}",
                anomaly_score=min(anomaly_score, 100),
                details={
                    'anomalies': anomalies,
                    'today_purchases': today_purchases,
                    'amount': str(instance.total_amount)
                }
            )
            
            # Créer une alerte de fraude si score élevé
            if anomaly_score >= 50:
                FraudAlert.objects.create(
                    pharmacie=instance.pharmacie,
                    alert_type='unusual_purchase_pattern',
                    severity='medium' if anomaly_score < 75 else 'high',
                    customer=instance.customer,
                    sale=instance,
                    description=f"Pattern d'achat inhabituel détecté",
                    indicators=anomalies,
                    risk_score=min(anomaly_score, 100)
                )


# ============================================================================
# SIGNALS PAIEMENTS
# ============================================================================

@receiver(post_save, sender=Payment)
def update_sale_status_on_payment(sender, instance, created, **kwargs):
    """Met à jour le statut de la vente lors du paiement"""
    if instance.status == 'completed':
        sale = instance.sale
        total_paid = sale.payments.filter(status='completed').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        # Si totalement payé, marquer comme terminé
        if total_paid >= sale.total_amount:
            sale.status = 'completed'
            sale.completed_at = timezone.now()
            sale.save(update_fields=['status', 'completed_at'])


@receiver(post_save, sender=Payment)
def increment_coupon_usage(sender, instance, created, **kwargs):
    """Incrémente le compteur d'utilisation du coupon"""
    if created and instance.sale.applied_coupon:
        coupon = instance.sale.applied_coupon
        coupon.current_uses = F('current_uses') + 1
        coupon.save(update_fields=['current_uses'])


# ============================================================================
# SIGNALS ORDONNANCES
# ============================================================================

@receiver(post_save, sender=ElectronicPrescription)
def detect_duplicate_prescriptions(sender, instance, created, **kwargs):
    """Détecte les ordonnances en double"""
    if created:
        # Chercher des ordonnances similaires
        duplicates = ElectronicPrescription.objects.filter(
            patient=instance.patient,
            doctor_name=instance.doctor_name,
            prescription_date=instance.prescription_date
        ).exclude(id=instance.id)
        
        if duplicates.exists():
            instance.is_duplicate = True
            instance.fraud_score += 40
            instance.fraud_flags.append('duplicate_detected')
            instance.save(update_fields=['is_duplicate', 'fraud_score', 'fraud_flags'])
            
            # Créer une alerte de fraude
            FraudAlert.objects.create(
                pharmacie=instance.pharmacie,
                alert_type='duplicate_prescription',
                severity='high',
                customer=instance.patient,
                prescription=instance,
                description='Ordonnance en double détectée',
                indicators=['same_patient', 'same_doctor', 'same_date'],
                risk_score=instance.fraud_score
            )


@receiver(post_save, sender=ElectronicPrescription)
def check_prescription_fraud_indicators(sender, instance, created, **kwargs):
    """Vérifie les indicateurs de fraude sur l'ordonnance"""
    if created or instance.status == 'pending':
        fraud_score = instance.fraud_score
        fraud_flags = instance.fraud_flags.copy() if instance.fraud_flags else []
        
        # 1. Vérifier si le patient a trop d'ordonnances récentes
        recent_prescriptions = ElectronicPrescription.objects.filter(
            patient=instance.patient,
            prescription_date__gte=timezone.now().date() - timedelta(days=7)
        ).count()
        
        if recent_prescriptions > 5:
            fraud_score += 20
            fraud_flags.append('too_many_recent_prescriptions')
        
        # 2. Vérifier si l'ordonnance expire rapidement (suspect)
        days_valid = (instance.expiry_date - instance.prescription_date).days
        if days_valid < 3:
            fraud_score += 15
            fraud_flags.append('short_validity_period')
        
        # 3. Vérifier les ordonnances du même médecin
        same_doctor = ElectronicPrescription.objects.filter(
            doctor_license=instance.doctor_license,
            patient=instance.patient,
            prescription_date__gte=timezone.now().date() - timedelta(days=30)
        ).count()
        
        if same_doctor > 10:
            fraud_score += 25
            fraud_flags.append('excessive_prescriptions_same_doctor')
        
        # Mettre à jour si changements
        if fraud_score != instance.fraud_score or fraud_flags != instance.fraud_flags:
            ElectronicPrescription.objects.filter(pk=instance.pk).update(
                fraud_score=min(fraud_score, 100),
                fraud_flags=fraud_flags
            )
            
            # Créer une alerte si score élevé
            if fraud_score >= 60:
                FraudAlert.objects.create(
                    pharmacie=instance.pharmacie,
                    alert_type='suspicious_prescription',
                    severity='high' if fraud_score >= 80 else 'medium',
                    customer=instance.patient,
                    prescription=instance,
                    description='Ordonnance suspecte détectée',
                    indicators=fraud_flags,
                    risk_score=min(fraud_score, 100)
                )


# ============================================================================
# SIGNALS RECOMMANDATIONS
# ============================================================================

@receiver(post_save, sender=Sale)
def update_product_recommendations(sender, instance, created, **kwargs):
    """Met à jour les recommandations de produits basées sur les ventes"""
    if instance.status == 'completed':
        items = list(instance.items.all())
        
        # Pour chaque paire de produits achetés ensemble
        for i, item1 in enumerate(items):
            for item2 in items[i+1:]:
                # Créer ou mettre à jour la recommandation
                rec, created = ProductRecommendation.objects.get_or_create(
                    source_product=item1.product,
                    recommended_product=item2.product,
                    defaults={
                        'recommendation_type': 'frequently_bought_together',
                        'confidence_score': Decimal('50.00'),
                        'times_bought_together': 1
                    }
                )
                
                if not created:
                    rec.times_bought_together = F('times_bought_together') + 1
                    # Augmenter le score de confiance
                    rec.confidence_score = min(
                        F('confidence_score') + Decimal('5.00'),
                        Decimal('100.00')
                    )
                    rec.save(update_fields=['times_bought_together', 'confidence_score'])


# ============================================================================
# SIGNALS ANALYTICS
# ============================================================================

@receiver(post_save, sender=Sale)
def trigger_analytics_update(sender, instance, **kwargs):
    """Déclenche la mise à jour des analytics (à exécuter de manière asynchrone avec Celery)"""
    # Cette fonction devrait idéalement appeler une tâche Celery
    # Pour l'instant, on peut juste marquer que les analytics doivent être recalculées
    pass


def calculate_product_performance(product, period_start, period_end):
    """Calcule la performance d'un produit sur une période"""
    sales = SaleItem.objects.filter(
        product=product,
        sale__status='completed',
        sale__sale_date__range=[period_start, period_end]
    )
    
    units_sold = sales.aggregate(total=Sum('quantity'))['total'] or 0
    revenue = sales.aggregate(total=Sum('line_total'))['total'] or Decimal('0.00')
    profit = sales.aggregate(total=Sum('profit_amount'))['total'] or Decimal('0.00')
    
    # Calculer la tendance (comparer avec la période précédente)
    period_duration = (period_end - period_start).days
    previous_start = period_start - timedelta(days=period_duration)
    previous_sales = SaleItem.objects.filter(
        product=product,
        sale__status='completed',
        sale__sale_date__range=[previous_start, period_start]
    )
    
    previous_units = previous_sales.aggregate(total=Sum('quantity'))['total'] or 0
    sales_trend = Decimal('0.00')
    
    if previous_units > 0:
        sales_trend = ((units_sold - previous_units) / previous_units) * 100
    
    # Déterminer si le produit est en baisse
    is_declining = sales_trend < -10
    
    # Recommander un réassort si nécessaire
    restock_recommended = product.is_low_stock() or (units_sold > product.stock_quantity * 0.5)
    recommended_quantity = max(units_sold * 2, product.min_stock_level * 2) if restock_recommended else 0
    
    # Créer ou mettre à jour la performance
    ProductPerformance.objects.update_or_create(
        product=product,
        period_start=period_start,
        defaults={
            'period_end': period_end,
            'units_sold': units_sold,
            'revenue': revenue,
            'profit': profit,
            'sales_trend': sales_trend,
            'is_declining': is_declining,
            'restock_recommended': restock_recommended,
            'recommended_quantity': recommended_quantity
        }
    )



# ============================================================================
# SIGNALS CAISSE ENREGISTREUSE
# ============================================================================

@receiver(post_save, sender=CashRegister)
def initialize_cash_register_balance(sender, instance, created, **kwargs):
    """Initialise le solde de la caisse lors de l'ouverture"""
    if created and instance.is_open:
        instance.current_balance = instance.opening_balance
        instance.expected_balance = instance.opening_balance
        CashRegister.objects.filter(pk=instance.pk).update(
            current_balance=instance.opening_balance,
            expected_balance=instance.opening_balance
        )


# ============================================================================
# SIGNALS TRANSACTIONS DE CAISSE
# ============================================================================

@receiver(post_save, sender=Payment)
def create_cash_transaction_from_payment(sender, instance, created, **kwargs):
    """Crée automatiquement une transaction de caisse pour les paiements en espèces"""
    if created and instance.payment_method == 'cash' and instance.status == 'completed':
        # Trouver la caisse ouverte du caissier (ou créer une transaction sans caisse)
        cash_register = CashRegister.objects.filter(
            cashier=instance.processed_by,
            is_open=True
        ).first()
        
        if cash_register:
            # Créer la transaction de caisse
            CashTransaction.objects.create(
                cash_register=cash_register,
                sale=instance.sale,
                transaction_type='sale',
                amount_due=instance.amount,
                amount_tendered=instance.amount,  # Par défaut, montant exact
                payment_method='cash',
                processed_by=instance.processed_by,
                transaction_date=instance.payment_date
            )


@receiver(post_save, sender=CashTransaction)
def check_change_availability(sender, instance, created, **kwargs):
    """Vérifie la disponibilité de la monnaie et crée des alertes si nécessaire"""
    if created and instance.change_amount > 0:
        # Vérifier si on a assez de monnaie pour chaque dénomination
        for denomination, quantity in instance.change_breakdown.items():
            if quantity > 0:
                # Ici vous pourriez implémenter une logique pour vérifier
                # le stock de monnaie réel dans la caisse
                # Pour l'instant, on crée juste un log si la quantité est importante
                
                denom_value = int(denomination)
                if quantity >= 5 and denom_value <= 1000:
                    # Alerte si on doit rendre beaucoup de petites coupures
                    ChangeShortage.objects.create(
                        cash_register=instance.cash_register,
                        denomination=denomination,
                        quantity_needed=quantity,
                        quantity_available=0,  # À mettre à jour avec le stock réel
                        shortage_amount=Decimal(str(denom_value * quantity)),
                        reported_by=instance.processed_by
                    )


@receiver(post_save, sender=CashTransaction)
def update_sale_payment_details(sender, instance, created, **kwargs):
    """Met à jour les détails de paiement de la vente"""
    if created and instance.sale:
        # Ajouter les détails de la transaction dans les métadonnées du paiement
        payments = instance.sale.payments.filter(payment_method='cash', status='completed')
        for payment in payments:
            payment.payment_details.update({
                'amount_tendered': str(instance.amount_tendered),
                'change_given': str(instance.change_amount),
                'change_breakdown': instance.change_breakdown
            })
            payment.save(update_fields=['payment_details'])


# ============================================================================
# SIGNALS COMPTAGE DE CAISSE
# ============================================================================

@receiver(post_save, sender=CashCount)
def update_cash_register_on_count(sender, instance, created, **kwargs):
    """Met à jour le solde de la caisse après un comptage"""
    if created:
        cash_register = instance.cash_register
        
        if instance.count_type == 'opening':
            # Comptage d'ouverture
            cash_register.opening_balance = instance.total_counted
            cash_register.current_balance = instance.total_counted
            cash_register.expected_balance = instance.total_counted
            
        elif instance.count_type == 'closing':
            # Comptage de fermeture
            cash_register.current_balance = instance.total_counted
            
            # Si écart important, créer une notification
            if abs(instance.discrepancy) > 1000:  # Écart > 1000 FCFA
                from gestion_communication.models import Notification
                
                severity = 'high' if abs(instance.discrepancy) > 5000 else 'normal'
                
                # Notifier le responsable
                if cash_register.cashier:
                    Notification.objects.create(
                        recipient=cash_register.cashier,
                        notification_type='system',
                        priority=severity,
                        title=f'⚠️ Écart de caisse détecté',
                        message=f'Écart de {instance.discrepancy:,.0f} FCFA lors de la fermeture de la caisse {cash_register.register_number}.',
                        send_in_app=True,
                        send_email=True,
                        data={
                            'cash_register_id': str(cash_register.id),
                            'discrepancy': str(instance.discrepancy),
                            'count_id': str(instance.id)
                        }
                    )
        
        cash_register.save()


@receiver(post_save, sender=CashCount)
def alert_on_significant_discrepancy(sender, instance, created, **kwargs):
    """Crée une alerte si l'écart est significatif"""
    if created and abs(instance.discrepancy) > 5000:  # Écart > 5000 FCFA
        from gestion_communication.models import Notification
        
        # Notifier les superviseurs/managers
        # (À adapter selon votre modèle de rôles)
        supervisors = instance.cash_register.pharmacie.employees.filter(
            role__name__in=['Manager', 'Superviseur', 'Gérant']
        )
        
        for supervisor in supervisors:
            Notification.objects.create(
                recipient=supervisor,
                notification_type='system',
                priority='urgent',
                title='🚨 Écart de caisse important',
                message=f'Écart de {instance.discrepancy:,.0f} FCFA détecté lors du comptage de la caisse {instance.cash_register.register_number}.',
                send_in_app=True,
                send_email=True,
                data={
                    'cash_register_id': str(instance.cash_register.id),
                    'discrepancy': str(instance.discrepancy),
                    'count_type': instance.count_type,
                    'counted_by': instance.counted_by.get_full_name() if instance.counted_by else 'N/A'
                }
            )


# ============================================================================
# SIGNALS MANQUE DE MONNAIE
# ============================================================================

@receiver(post_save, sender=ChangeShortage)
def notify_change_shortage(sender, instance, created, **kwargs):
    """Notifie les responsables en cas de manque de monnaie"""
    if created and not instance.is_resolved:
        from gestion_communication.models import Notification
        
        # Notifier le caissier et les superviseurs
        recipients = [instance.cash_register.cashier]
        
        # Ajouter les superviseurs
        supervisors = instance.cash_register.pharmacie.employees.filter(
            role__name__in=['Manager', 'Superviseur', 'Gérant']
        )
        recipients.extend(supervisors)
        
        for recipient in recipients:
            if recipient:
                Notification.objects.create(
                    recipient=recipient,
                    notification_type='system',
                    priority='normal',
                    title=f'💰 Manque de monnaie',
                    message=f'Manque de {instance.quantity_needed - instance.quantity_available} billet(s)/pièce(s) de {instance.denomination} FCFA à la caisse {instance.cash_register.register_number}.',
                    send_in_app=True,
                    data={
                        'cash_register_id': str(instance.cash_register.id),
                        'denomination': instance.denomination,
                        'quantity_needed': instance.quantity_needed
                    }
                )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_suggested_tender_amount(amount_due):
    """
    Suggère un montant à verser pour faciliter la monnaie à rendre
    Arrondit au montant supérieur le plus proche qui simplifie la monnaie
    """
    # Dénominations courantes pour arrondir
    round_to = [10000, 5000, 2000, 1000, 500]
    
    for denom in round_to:
        if amount_due <= denom:
            return Decimal(str(denom))
        elif amount_due % denom < denom / 2:
            # Arrondir au multiple inférieur
            return Decimal(str((amount_due // denom) * denom + denom))
    
    # Si montant très élevé, arrondir au millier supérieur
    return Decimal(str(((amount_due // 1000) + 1) * 1000))


def calculate_optimal_change(change_amount, available_denominations):
    """
    Calcule la combinaison optimale de billets/pièces pour rendre la monnaie
    en fonction des dénominations disponibles
    
    Args:
        change_amount: Montant à rendre
        available_denominations: Dict {denomination: quantity_available}
    
    Returns:
        Dict {denomination: quantity_to_give} ou None si impossible
    """
    result = {}
    remaining = float(change_amount)
    
    # Trier par dénomination décroissante
    sorted_denoms = sorted(
        [(int(d), q) for d, q in available_denominations.items()],
        reverse=True
    )
    
    for denom_value, qty_available in sorted_denoms:
        if remaining >= denom_value and qty_available > 0:
            qty_needed = min(int(remaining // denom_value), qty_available)
            if qty_needed > 0:
                result[str(denom_value)] = qty_needed
                remaining -= qty_needed * denom_value
                remaining = round(remaining, 2)
    
    # Vérifier si on a pu tout rendre
    if remaining > 0.01:  # Tolérance pour erreurs de virgule flottante
        return None  # Impossible de rendre la monnaie exacte
    
    return result
