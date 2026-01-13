"""
Signals pour la gestion financière
Automatisation complète : numérotation, calculs, prévisions, alertes
"""
from django.db.models.signals import post_save, pre_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.utils import timezone
from django.db.models import Sum, Q, F, Avg
from datetime import timedelta
from decimal import Decimal
import hashlib
import secrets

from gestion_finance.models import (
    Currency, TaxRate, Invoice, InvoiceItem, CreditNote, Payment,
    CustomerCredit, CreditPayment, ExpenseCategory, Expense,
    FinancialForecast, TaxReport
)


# ============================================================================
# NUMÉROTATION AUTOMATIQUE
# ============================================================================

@receiver(pre_save, sender=Invoice)
def generate_invoice_number(sender, instance, **kwargs):
    """Génère automatiquement le numéro de facture"""
    if not instance.invoice_number:
        year = timezone.now().year
        prefix = {
            'counter_sale': 'INV-CS',
            'online_sale': 'INV-ON',
            'prescription': 'INV-PR',
            'other': 'INV-OT'
        }.get(instance.invoice_type, 'INV')
        
        count = Invoice.objects.filter(
            pharmacie=instance.pharmacie,
            issue_date__year=year,
            invoice_type=instance.invoice_type
        ).count() + 1
        
        instance.invoice_number = f"{prefix}-{year}-{count:06d}"


@receiver(pre_save, sender=CreditNote)
def generate_credit_note_number(sender, instance, **kwargs):
    """Génère automatiquement le numéro d'avoir"""
    if not instance.credit_note_number:
        year = timezone.now().year
        count = CreditNote.objects.filter(
            pharmacie=instance.pharmacie,
            issue_date__year=year
        ).count() + 1
        instance.credit_note_number = f"CN-{year}-{count:06d}"


@receiver(pre_save, sender=Payment)
def generate_payment_number(sender, instance, **kwargs):
    """Génère automatiquement le numéro de paiement"""
    if not instance.payment_number:
        date_str = timezone.now().strftime('%Y%m%d')
        count = Payment.objects.filter(
            pharmacie=instance.pharmacie,
            payment_date__date=timezone.now().date()
        ).count() + 1
        instance.payment_number = f"PAY-{date_str}-{count:04d}"


@receiver(pre_save, sender=Expense)
def generate_expense_number(sender, instance, **kwargs):
    """Génère automatiquement le numéro de dépense"""
    if not instance.expense_number:
        year = timezone.now().year
        count = Expense.objects.filter(
            pharmacie=instance.pharmacie,
            expense_date__year=year
        ).count() + 1
        instance.expense_number = f"EXP-{year}-{count:06d}"


@receiver(pre_save, sender=TaxReport)
def generate_tax_report_number(sender, instance, **kwargs):
    """Génère automatiquement le numéro de rapport fiscal"""
    if not instance.report_number:
        year = instance.period_end.year
        month = instance.period_end.month
        count = TaxReport.objects.filter(
            pharmacie=instance.pharmacie,
            period_end__year=year,
            period_end__month=month
        ).count() + 1
        instance.report_number = f"TAX-{year}{month:02d}-{count:03d}"


# ============================================================================
# GESTION DES FACTURES
# ============================================================================

@receiver(post_save, sender=InvoiceItem)
@receiver(post_delete, sender=InvoiceItem)
def update_invoice_totals(sender, instance, **kwargs):
    """Recalcule les totaux de la facture"""
    invoice = instance.invoice
    totals = invoice.calculate_totals()
    
    Invoice.objects.filter(id=invoice.id).update(
        subtotal=totals['subtotal'],
        tax_amount=totals['tax_amount'],
        total_amount=totals['total_amount'],
        balance_due=totals['balance_due']
    )


@receiver(post_save, sender=Invoice)
def update_invoice_status_on_save(sender, instance, created, **kwargs):
    """Met à jour le statut de la facture selon les paiements et dates"""
    if created:
        return
    
    # Vérifier si en retard
    if instance.is_overdue() and instance.status not in ['paid', 'cancelled', 'credited']:
        instance.status = 'overdue'
        instance.save(update_fields=['status'])
    
    # Vérifier si payée
    if instance.paid_amount >= instance.total_amount and instance.status != 'paid':
        instance.status = 'paid'
        instance.paid_date = timezone.now().date()
        instance.save(update_fields=['status', 'paid_date'])
    elif instance.paid_amount > 0 and instance.paid_amount < instance.total_amount:
        if instance.status not in ['partially_paid', 'overdue']:
            instance.status = 'partially_paid'
            instance.save(update_fields=['status'])


@receiver(post_save, sender=Payment)
def update_invoice_on_payment(sender, instance, created, **kwargs):
    """Met à jour la facture lors d'un paiement"""
    if created and instance.status == 'completed':
        invoice = instance.invoice
        
        # Mettre à jour le montant payé
        invoice.paid_amount = F('paid_amount') + instance.amount
        invoice.balance_due = F('total_amount') - F('paid_amount')
        invoice.save()
        invoice.refresh_from_db()
        
        # Mettre à jour le statut
        if invoice.paid_amount >= invoice.total_amount:
            invoice.status = 'paid'
            invoice.paid_date = timezone.now().date()
            invoice.save(update_fields=['status', 'paid_date'])
        elif invoice.paid_amount > 0:
            invoice.status = 'partially_paid'
            invoice.save(update_fields=['status'])


@receiver(post_save, sender=CreditNote)
def apply_credit_note_to_invoice(sender, instance, created, **kwargs):
    """Applique l'avoir à la facture d'origine"""
    if created:
        original_invoice = instance.original_invoice
        
        # Réduire le montant dû
        original_invoice.balance_due = F('balance_due') - instance.credit_amount
        original_invoice.save()
        original_invoice.refresh_from_db()
        
        # Marquer la facture comme "avoir émis"
        if original_invoice.status not in ['cancelled', 'credited']:
            original_invoice.status = 'credited'
            original_invoice.credit_note = instance
            original_invoice.save(update_fields=['status', 'credit_note'])


# ============================================================================
# GESTION DES CRÉDITS CLIENTS
# ============================================================================

@receiver(post_save, sender=Invoice)
def create_customer_credit_if_needed(sender, instance, created, **kwargs):
    """Crée un crédit client si paiement différé"""
    if created and instance.due_date and instance.balance_due > 0:
        if instance.customer and instance.status in ['issued', 'overdue']:
            CustomerCredit.objects.get_or_create(
                pharmacie=instance.pharmacie,
                customer=instance.customer,
                invoice=instance,
                defaults={
                    'credit_amount': instance.balance_due,
                    'balance_due': instance.balance_due,
                    'credit_date': instance.issue_date,
                    'due_date': instance.due_date,
                    'status': 'active'
                }
            )


@receiver(post_save, sender=CreditPayment)
def update_customer_credit_on_payment(sender, instance, created, **kwargs):
    """Met à jour le crédit client lors d'un paiement"""
    if created:
        credit = instance.credit
        
        # Mettre à jour les montants
        credit.paid_amount = F('paid_amount') + instance.amount
        credit.balance_due = F('balance_due') - instance.amount
        credit.save()
        credit.refresh_from_db()
        
        # Mettre à jour le statut
        if credit.balance_due <= 0:
            credit.status = 'paid'
        elif credit.paid_amount > 0:
            credit.status = 'partially_paid'
        
        credit.save(update_fields=['status'])


@receiver(post_save, sender=CustomerCredit)
def check_credit_overdue(sender, instance, **kwargs):
    """Vérifie si le crédit est en retard"""
    if instance.is_overdue() and instance.status not in ['paid', 'written_off']:
        instance.status = 'overdue'
        instance.save(update_fields=['status'])


# ============================================================================
# GESTION DES DEVISES
# ============================================================================

@receiver(post_save, sender=Currency)
def ensure_single_default_currency(sender, instance, **kwargs):
    """Assure qu'une seule devise est par défaut"""
    if instance.is_default:
        Currency.objects.exclude(id=instance.id).update(is_default=False)


@receiver(pre_save, sender=Invoice)
def set_exchange_rate(sender, instance, **kwargs):
    """Définit le taux de change au moment de la création"""
    if not instance.exchange_rate or instance.exchange_rate == Decimal('1.000000'):
        if instance.currency:
            instance.exchange_rate = instance.currency.exchange_rate


# ============================================================================
# GESTION DES TAXES
# ============================================================================

@receiver(post_save, sender=TaxRate)
def ensure_single_default_tax(sender, instance, **kwargs):
    """Assure qu'une seule taxe est par défaut par pharmacie"""
    if instance.is_default:
        TaxRate.objects.filter(
            pharmacie=instance.pharmacie
        ).exclude(id=instance.id).update(is_default=False)


# ============================================================================
# GÉNÉRATION DE HASH DE VÉRIFICATION
# ============================================================================

@receiver(pre_save, sender=Invoice)
def generate_invoice_verification_hash(sender, instance, **kwargs):
    """Génère le hash de vérification de la facture"""
    if not instance.verification_hash:
        data = f"{instance.invoice_number}{instance.pharmacie.id}{instance.total_amount}{secrets.token_hex(16)}"
        instance.verification_hash = hashlib.sha256(data.encode()).hexdigest()


# ============================================================================
# PRÉVISIONS FINANCIÈRES (IA)
# ============================================================================

@receiver(post_save, sender=Invoice)
@receiver(post_save, sender=Expense)
def trigger_financial_forecast_update(sender, instance, created, **kwargs):
    """Déclenche une mise à jour des prévisions financières"""
    if created:
        # Récupérer la pharmacie
        pharmacie = instance.pharmacie
        
        # Calculer les prévisions pour le mois prochain
        forecast_date = (timezone.now() + timedelta(days=30)).date()
        
        # Prévision de revenus
        if sender == Invoice and instance.status != 'cancelled':
            create_or_update_revenue_forecast(pharmacie, forecast_date)
        
        # Prévision de dépenses
        if sender == Expense and instance.status != 'rejected':
            create_or_update_expense_forecast(pharmacie, forecast_date)


def create_or_update_revenue_forecast(pharmacie, forecast_date):
    """Crée ou met à jour la prévision de revenus"""
    # Calculer la moyenne des revenus des 3 derniers mois
    three_months_ago = timezone.now().date() - timedelta(days=90)
    
    total_revenue = Invoice.objects.filter(
        pharmacie=pharmacie,
        issue_date__gte=three_months_ago,
        status__in=['issued', 'paid', 'partially_paid']
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    # Moyenne mensuelle
    monthly_average = total_revenue / 3
    
    # Facteur saisonnier (simplifié)
    current_month = forecast_date.month
    seasonal_factors = {
        12: 1.2, 1: 1.2, 2: 1.1,  # Hiver
        3: 1.0, 4: 0.9, 5: 0.9,    # Printemps
        6: 0.8, 7: 0.8, 8: 0.8,    # Été
        9: 0.9, 10: 1.0, 11: 1.1   # Automne
    }
    seasonal_factor = Decimal(str(seasonal_factors.get(current_month, 1.0)))
    
    # Prévision ajustée
    predicted_amount = monthly_average * seasonal_factor
    
    # Niveau de confiance basé sur la variabilité
    confidence = 75 if total_revenue > 0 else 30
    
    # Créer ou mettre à jour la prévision
    FinancialForecast.objects.update_or_create(
        pharmacie=pharmacie,
        forecast_type='revenue',
        forecast_date=forecast_date,
        period='monthly',
        defaults={
            'predicted_amount': predicted_amount,
            'confidence_level': Decimal(str(confidence)),
            'seasonal_factor': seasonal_factor,
            'trend_factor': Decimal('1.0'),
            'algorithm_used': 'Simple Moving Average with Seasonal Adjustment',
            'data_points_used': 3
        }
    )


def create_or_update_expense_forecast(pharmacie, forecast_date):
    """Crée ou met à jour la prévision de dépenses"""
    # Calculer la moyenne des dépenses des 3 derniers mois
    three_months_ago = timezone.now().date() - timedelta(days=90)
    
    total_expenses = Expense.objects.filter(
        pharmacie=pharmacie,
        expense_date__gte=three_months_ago,
        status__in=['approved', 'paid']
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    # Moyenne mensuelle
    monthly_average = total_expenses / 3
    
    # Facteur de tendance (croissance de 5% par défaut)
    trend_factor = Decimal('1.05')
    
    # Prévision
    predicted_amount = monthly_average * trend_factor
    
    # Niveau de confiance
    confidence = 70 if total_expenses > 0 else 25
    
    # Créer ou mettre à jour la prévision
    FinancialForecast.objects.update_or_create(
        pharmacie=pharmacie,
        forecast_type='expense',
        forecast_date=forecast_date,
        period='monthly',
        defaults={
            'predicted_amount': predicted_amount,
            'confidence_level': Decimal(str(confidence)),
            'seasonal_factor': Decimal('1.0'),
            'trend_factor': trend_factor,
            'algorithm_used': 'Simple Moving Average with Trend',
            'data_points_used': 3
        }
    )


@receiver(post_save, sender=FinancialForecast)
def update_forecast_variance(sender, instance, **kwargs):
    """Met à jour l'écart de prévision si le montant réel est disponible"""
    if instance.actual_amount is not None and instance.variance is None:
        instance.variance = instance.calculate_variance()
        instance.save(update_fields=['variance'])


# ============================================================================
# RAPPORTS FISCAUX AUTOMATIQUES
# ============================================================================

@receiver(post_save, sender=Invoice)
@receiver(post_save, sender=Expense)
def check_monthly_tax_report(sender, instance, created, **kwargs):
    """Vérifie si un rapport fiscal mensuel doit être généré"""
    if not created:
        return
    
    pharmacie = instance.pharmacie
    now = timezone.now()
    
    # Vérifier si c'est le premier jour du mois
    if now.day == 1:
        # Générer le rapport pour le mois précédent
        previous_month = now - timedelta(days=1)
        period_start = previous_month.replace(day=1).date()
        period_end = previous_month.date()
        
        # Vérifier si le rapport existe déjà
        existing_report = TaxReport.objects.filter(
            pharmacie=pharmacie,
            period_start=period_start,
            period_end=period_end
        ).exists()
        
        if not existing_report:
            generate_monthly_tax_report(pharmacie, period_start, period_end)


def generate_monthly_tax_report(pharmacie, period_start, period_end):
    """Génère un rapport fiscal mensuel"""
    # Calculer les revenus
    total_revenue = Invoice.objects.filter(
        pharmacie=pharmacie,
        issue_date__range=(period_start, period_end),
        status__in=['issued', 'paid', 'partially_paid']
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    # Calculer les taxes collectées
    total_tax = Invoice.objects.filter(
        pharmacie=pharmacie,
        issue_date__range=(period_start, period_end),
        status__in=['issued', 'paid', 'partially_paid']
    ).aggregate(total=Sum('tax_amount'))['total'] or Decimal('0.00')
    
    # Calculer les dépenses
    total_expenses = Expense.objects.filter(
        pharmacie=pharmacie,
        expense_date__range=(period_start, period_end),
        status__in=['approved', 'paid']
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    # Calculer le bénéfice net
    net_profit = total_revenue - total_expenses
    
    # Créer le rapport
    TaxReport.objects.create(
        pharmacie=pharmacie,
        report_type='comprehensive',
        period_start=period_start,
        period_end=period_end,
        total_revenue=total_revenue,
        total_tax_collected=total_tax,
        total_expenses=total_expenses,
        net_profit=net_profit,
        status='generated'
    )


# ============================================================================
# ALERTES DE PAIEMENT
# ============================================================================

@receiver(post_save, sender=CustomerCredit)
def send_payment_reminder(sender, instance, created, **kwargs):
    """Envoie un rappel de paiement si proche de l'échéance"""
    if instance.status in ['active', 'partially_paid']:
        days_until_due = (instance.due_date - timezone.now().date()).days
        
        # Rappel 7 jours avant l'échéance
        if days_until_due == 7:
            # TODO: Envoyer email/SMS de rappel
            pass
        
        # Rappel le jour de l'échéance
        elif days_until_due == 0:
            # TODO: Envoyer email/SMS urgent
            pass


# ============================================================================
# VALIDATION DES DÉPENSES
# ============================================================================

@receiver(post_save, sender=Expense)
def auto_approve_small_expenses(sender, instance, created, **kwargs):
    """Approuve automatiquement les petites dépenses"""
    if created and instance.status == 'pending':
        # Seuil d'auto-approbation (ex: 50,000 XAF)
        auto_approve_threshold = Decimal('50000.00')
        
        if instance.amount <= auto_approve_threshold:
            instance.status = 'approved'
            instance.approved_at = timezone.now()
            instance.save(update_fields=['status', 'approved_at'])


# ============================================================================
# HELPERS
# ============================================================================

def calculate_profit_forecast(pharmacie, forecast_date):
    """Calcule la prévision de bénéfice"""
    # Récupérer les prévisions de revenus et dépenses
    revenue_forecast = FinancialForecast.objects.filter(
        pharmacie=pharmacie,
        forecast_type='revenue',
        forecast_date=forecast_date,
        period='monthly'
    ).first()
    
    expense_forecast = FinancialForecast.objects.filter(
        pharmacie=pharmacie,
        forecast_type='expense',
        forecast_date=forecast_date,
        period='monthly'
    ).first()
    
    if revenue_forecast and expense_forecast:
        predicted_profit = revenue_forecast.predicted_amount - expense_forecast.predicted_amount
        
        # Niveau de confiance (moyenne des deux)
        confidence = (revenue_forecast.confidence_level + expense_forecast.confidence_level) / 2
        
        # Créer la prévision de bénéfice
        FinancialForecast.objects.update_or_create(
            pharmacie=pharmacie,
            forecast_type='profit',
            forecast_date=forecast_date,
            period='monthly',
            defaults={
                'predicted_amount': predicted_profit,
                'confidence_level': confidence,
                'seasonal_factor': Decimal('1.0'),
                'trend_factor': Decimal('1.0'),
                'algorithm_used': 'Revenue - Expenses',
                'data_points_used': 2
            }
        )