"""
Signals pour le Suivi Médical & CRM Marketing
Automatisation complète : numérotation, alertes, rappels, fidélité, IA
Applications 7 & 8
"""
from django.db.models.signals import post_save, pre_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.utils import timezone
from django.db.models import Sum, Count, Q, F, Avg, Max
from datetime import timedelta, date
from decimal import Decimal
import hashlib
from gestion_suivit.models import(
    Doctor,MedicalProfile,DoctorPatientLink,MedicalCondition,PatientCondition,
    Allergen,Prescription,PrescriptionItem,Treatment,TreatmentMedication,ExternalMedicalRecord,
    Appointment,PatientMessage,LoyaltyProgram,LoyaltyTier,LoyaltyTransaction,CustomerLoyalty,
    MarketingCampaign,CampaignRecipient,CustomerSegment,Lead,AutomatedReminder
)
from gestion_rh.models import Client



# ============================================================================
# NUMÉROTATION AUTOMATIQUE
# ============================================================================

@receiver(pre_save, sender='gestion_suivit.Doctor')
def generate_doctor_code(sender, instance, **kwargs):
    """Génère automatiquement le code médecin"""
    if not instance.doctor_code:
        pharmacy_id = instance.pharmacie.id
        count = sender.objects.filter(pharmacie=instance.pharmacie).count() + 1
        instance.doctor_code = f"DR-{pharmacy_id}-{count:05d}"


@receiver(pre_save, sender='gestion_suivit.Prescription')
def generate_prescription_number(sender, instance, **kwargs):
    """Génère automatiquement le numéro d'ordonnance"""
    if not instance.prescription_number:
        year = timezone.now().year
        count = sender.objects.filter(
            patient__pharmacie=instance.patient.pharmacie,
            prescription_date__year=year
        ).count() + 1
        instance.prescription_number = f"ORD-{year}-{count:06d}"


# ============================================================================
# GESTION PROFIL MÉDICAL
# ============================================================================

@receiver(post_save, sender='gestion_rh.Client')
def create_medical_profile(sender, instance, created, **kwargs):
    """Crée automatiquement un profil médical pour chaque nouveau client"""
    if created:
        from .models import MedicalProfile
        MedicalProfile.objects.get_or_create(
            patient=instance,
            defaults={
                'consent_data_usage': False,
                'consent_communication': False
            }
        )


@receiver(post_save, sender='gestion_suivit.DoctorPatientLink')
def update_primary_doctor(sender, instance, created, **kwargs):
    """Met à jour le médecin traitant dans le profil médical"""
    if instance.is_primary:
        # S'assurer qu'un seul médecin est primaire
        sender.objects.filter(
            patient=instance.patient,
            is_primary=True
        ).exclude(id=instance.id).update(is_primary=False)
        
        # Mettre à jour le profil médical
        medical_profile = instance.patient.medical_profile
        medical_profile.primary_doctor = instance.doctor
        medical_profile.save(update_fields=['primary_doctor'])


# ============================================================================
# GESTION ALLERGIES - ALERTES CRITIQUES
# ============================================================================

@receiver(post_save, sender='gestion_suivit.PatientAllergy')
def check_allergy_conflicts(sender, instance, created, **kwargs):
    """Vérifie les conflits allergies avec traitements en cours"""
    if created and instance.severity in ['severe', 'life_threatening']:
        # Vérifier les traitements actifs
        from .models import Treatment, TreatmentMedication
        
        active_treatments = Treatment.objects.filter(
            patient=instance.patient,
            status='active'
        )
        
        for treatment in active_treatments:
            # Vérifier si un médicament du traitement contient l'allergène
            medications = treatment.medications.filter(
                is_active=True,
                product__name__icontains=instance.allergen.name
            )
            
            if medications.exists():
                # Créer une alerte critique
                create_critical_allergy_alert(
                    patient=instance.patient,
                    allergy=instance,
                    treatment=treatment
                )


def create_critical_allergy_alert(patient, allergy, treatment):
    """Crée une alerte critique d'allergie"""
    # TODO: Implémenter système d'alerte
    # Envoyer notification au pharmacien
    # Suspendre temporairement le traitement
    pass


# ============================================================================
# GESTION ORDONNANCES
# ============================================================================

@receiver(post_save, sender='gestion_suivit.Prescription')
def check_prescription_expiry(sender, instance, created, **kwargs):
    """Vérifie l'expiration de l'ordonnance"""
    if instance.status == 'active' and instance.is_expired():
        instance.status = 'expired'
        instance.save(update_fields=['status'])


@receiver(post_save, sender='gestion_suivit.PrescriptionItem')
def update_prescription_dispensation(sender, instance, **kwargs):
    """Met à jour le statut de délivrance de l'ordonnance"""
    prescription = instance.prescription
    
    # Vérifier si tous les items sont délivrés
    items = prescription.items.all()
    all_dispensed = all(
        item.quantity_dispensed >= item.quantity 
        for item in items
    )
    
    if all_dispensed and prescription.status == 'active':
        prescription.status = 'completed'
        prescription.dispensed_at = timezone.now()
        prescription.save(update_fields=['status', 'dispensed_at'])


# ============================================================================
# GESTION TRAITEMENTS - RAPPELS AUTOMATIQUES
# ============================================================================

@receiver(post_save, sender='gestion_suivit.Treatment')
def create_treatment_reminders(sender, instance, created, **kwargs):
    """Crée des rappels automatiques pour le traitement"""
    if created and instance.reminder_enabled:
        from .models import AutomatedReminder
        
        # Calculer les dates de rappel selon la fréquence
        reminder_dates = calculate_reminder_dates(
            start_date=instance.start_date,
            end_date=instance.end_date,
            frequency=instance.reminder_frequency
        )
        
        for reminder_date in reminder_dates:
            AutomatedReminder.objects.create(
                pharmacie=instance.patient.pharmacie,
                customer=instance.patient,
                reminder_type='medication_time',
                treatment=instance,
                message=f"Rappel : Prendre votre traitement {instance.name}",
                send_via_sms=True,
                send_via_push=True,
                scheduled_datetime=reminder_date,
                status='pending'
            )


@receiver(post_save, sender='gestion_suivit.Treatment')
def check_treatment_renewal(sender, instance, **kwargs):
    """Crée un rappel de renouvellement de traitement"""
    if instance.end_date and instance.status == 'active':
        from .models import AutomatedReminder
        
        # Créer un rappel 7 jours avant la fin
        reminder_date = instance.end_date - timedelta(days=7)
        
        if reminder_date >= timezone.now().date():
            AutomatedReminder.objects.get_or_create(
                pharmacie=instance.patient.pharmacie,
                customer=instance.patient,
                reminder_type='medication_renewal',
                treatment=instance,
                scheduled_datetime=timezone.make_aware(
                    timezone.datetime.combine(reminder_date, timezone.datetime.min.time())
                ),
                defaults={
                    'message': f"Votre traitement {instance.name} arrive à expiration. Pensez à renouveler votre ordonnance.",
                    'send_via_sms': True,
                    'send_via_email': True,
                    'status': 'pending'
                }
            )


def calculate_reminder_dates(start_date, end_date, frequency):
    """Calcule les dates de rappel selon la fréquence"""
    reminders = []
    current_date = start_date
    
    if not end_date:
        end_date = start_date + timedelta(days=30)  # Par défaut 30 jours
    
    # Mapping fréquences
    frequency_map = {
        'daily': 1,
        'twice_daily': 0.5,
        'three_times_daily': 0.33,
        'weekly': 7,
        'twice_weekly': 3.5,
    }
    
    interval_days = frequency_map.get(frequency, 1)
    
    while current_date <= end_date:
        reminder_datetime = timezone.make_aware(
            timezone.datetime.combine(current_date, timezone.datetime.min.time().replace(hour=9))
        )
        reminders.append(reminder_datetime)
        
        if interval_days < 1:
            # Plusieurs fois par jour
            times_per_day = int(1 / interval_days)
            for i in range(1, times_per_day):
                hour = 9 + (12 // times_per_day) * i
                reminder_datetime = timezone.make_aware(
                    timezone.datetime.combine(current_date, timezone.datetime.min.time().replace(hour=hour))
                )
                reminders.append(reminder_datetime)
            current_date += timedelta(days=1)
        else:
            current_date += timedelta(days=int(interval_days))
    
    return reminders


# ============================================================================
# GESTION RENDEZ-VOUS - RAPPELS
# ============================================================================

@receiver(post_save, sender='gestion_suivit.Appointment')
def create_appointment_reminder(sender, instance, created, **kwargs):
    """Crée un rappel automatique pour le rendez-vous"""
    if created and instance.status in ['scheduled', 'confirmed']:
        from .models import AutomatedReminder
        
        # Rappel 24h avant
        reminder_date = instance.appointment_datetime - timedelta(hours=24)
        
        if reminder_date > timezone.now():
            AutomatedReminder.objects.create(
                pharmacie=instance.pharmacie,
                customer=instance.patient,
                reminder_type='appointment',
                appointment=instance,
                message=f"Rappel : Rendez-vous demain à {instance.appointment_datetime.strftime('%H:%M')} - {instance.get_appointment_type_display()}",
                send_via_sms=True,
                send_via_email=True,
                send_via_push=True,
                scheduled_datetime=reminder_date,
                status='pending'
            )


# ============================================================================
# PROGRAMME FIDÉLITÉ - GESTION AUTOMATIQUE DES POINTS
# ============================================================================

@receiver(post_save, sender='gestion_rh.Client')
def create_loyalty_account(sender, instance, created, **kwargs):
    """Crée automatiquement un compte fidélité pour chaque nouveau client"""
    if created:
        from .models import LoyaltyProgram, CustomerLoyalty
        
        try:
            program = LoyaltyProgram.objects.get(
                pharmacie=instance.pharmacie,
                is_active=True
            )
            CustomerLoyalty.objects.create(
                customer=instance,
                program=program,
                enrolled_date=timezone.now().date()
            )
        except LoyaltyProgram.DoesNotExist:
            pass


@receiver(post_save, sender='gestion_vente.Sale')
def award_loyalty_points(sender, instance, created, **kwargs):
    """Attribue des points de fidélité après un achat"""
    if instance.status == 'completed':
        from .models import CustomerLoyalty, LoyaltyTransaction, LoyaltyProgram
        
        try:
            loyalty_account = CustomerLoyalty.objects.get(
                customer=instance.customer,
                is_active=True
            )
            program = loyalty_account.program
            
            # Calculer les points
            points_earned = int(float(instance.total_amount) * float(program.points_per_xaf))
            
            # Appliquer multiplicateur du niveau
            if loyalty_account.current_tier:
                points_earned = int(points_earned * float(loyalty_account.current_tier.points_multiplier))
            
            # Créer la transaction
            expiry_date = timezone.now().date() + timedelta(days=30 * program.points_expiry_months)
            
            LoyaltyTransaction.objects.create(
                customer_loyalty=loyalty_account,
                transaction_type='earn',
                points=points_earned,
                sale=instance,
                description=f"Achat {instance.sale_number}",
                expires_at=expiry_date
            )
            
            # Mettre à jour le compte
            loyalty_account.total_points_earned += points_earned
            loyalty_account.points_balance += points_earned
            loyalty_account.total_purchases += 1
            loyalty_account.total_amount_spent += instance.total_amount
            loyalty_account.last_activity_date = timezone.now().date()
            loyalty_account.save()
            
            # Vérifier changement de niveau
            check_loyalty_tier_upgrade(loyalty_account)
            
        except CustomerLoyalty.DoesNotExist:
            pass


def check_loyalty_tier_upgrade(loyalty_account):
    """Vérifie et applique un changement de niveau de fidélité"""
    from .models import LoyaltyTier
    
    if not loyalty_account.program.enable_tiers:
        return
    
    # Trouver le niveau approprié
    eligible_tiers = LoyaltyTier.objects.filter(
        program=loyalty_account.program,
        is_active=True,
        min_points__lte=loyalty_account.points_balance,
        min_purchases__lte=loyalty_account.total_purchases,
        min_amount_spent__lte=loyalty_account.total_amount_spent
    ).order_by('-level')
    
    if eligible_tiers.exists():
        new_tier = eligible_tiers.first()
        if new_tier != loyalty_account.current_tier:
            old_tier = loyalty_account.current_tier
            loyalty_account.current_tier = new_tier
            loyalty_account.save()
            
            # Créer notification de changement de niveau
            send_tier_upgrade_notification(loyalty_account, old_tier, new_tier)


def send_tier_upgrade_notification(loyalty_account, old_tier, new_tier):
    """Envoie une notification de changement de niveau"""
    # TODO: Implémenter envoi notification
    message = f"Félicitations ! Vous passez au niveau {new_tier.name} !"
    pass


@receiver(post_save, sender='gestion_suivit.LoyaltyTransaction')
def expire_loyalty_points(sender, instance, created, **kwargs):
    """Vérifie l'expiration des points de fidélité"""
    if instance.expires_at and instance.expires_at <= timezone.now().date():
        if instance.transaction_type == 'earn' and instance.points > 0:
            loyalty_account = instance.customer_loyalty
            
            # Créer transaction d'expiration
            sender.objects.create(
                customer_loyalty=loyalty_account,
                transaction_type='expire',
                points=-instance.points,
                description=f"Expiration des points du {instance.transaction_date.strftime('%d/%m/%Y')}"
            )
            
            # Mettre à jour le solde
            loyalty_account.points_balance -= instance.points
            loyalty_account.points_expired += instance.points
            loyalty_account.save()


# ============================================================================
# RAPPELS ANNIVERSAIRE ET PROMOTIONS
# ============================================================================

@receiver(post_save, sender='gestion_rh.Client')
def schedule_birthday_reminder(sender, instance, created, **kwargs):
    """Planifie un rappel d'anniversaire annuel"""
    if instance.date_of_birth:
        from .models import AutomatedReminder
        
        # Calculer le prochain anniversaire
        today = timezone.now().date()
        next_birthday = date(today.year, instance.date_of_birth.month, instance.date_of_birth.day)
        
        if next_birthday < today:
            next_birthday = date(today.year + 1, instance.date_of_birth.month, instance.date_of_birth.day)
        
        # Créer rappel pour le jour J
        AutomatedReminder.objects.get_or_create(
            pharmacie=instance.pharmacie,
            customer=instance,
            reminder_type='birthday',
            scheduled_datetime=timezone.make_aware(
                timezone.datetime.combine(next_birthday, timezone.datetime.min.time().replace(hour=9))
            ),
            defaults={
                'message': f"Joyeux anniversaire {instance.first_name} ! Profitez de votre cadeau spécial !",
                'send_via_sms': True,
                'send_via_email': True,
                'status': 'pending'
            }
        )


# ============================================================================
# DÉTECTION CLIENTS INACTIFS
# ============================================================================

@receiver(post_save, sender='gestion_vente.Sale')
def reset_inactive_customer_timer(sender, instance, **kwargs):
    """Réinitialise le timer d'inactivité après un achat"""
    if instance.status == 'completed':
        # Annuler les rappels d'inactivité en attente
        from .models import AutomatedReminder
        
        AutomatedReminder.objects.filter(
            customer=instance.customer,
            reminder_type='inactive_customer',
            status='pending'
        ).update(status='cancelled')


def check_inactive_customers():
    """
    Fonction périodique (à appeler via Celery/Cron)
    Détecte les clients inactifs et crée des rappels
    """
    from .models import AutomatedReminder
    from django.db.models import Max
    
    # Clients sans achat depuis 90 jours
    inactive_threshold = timezone.now().date() - timedelta(days=90)
    
    inactive_customers = Client.objects.annotate(
        last_purchase=Max('sales__sale_date')
    ).filter(
        Q(last_purchase__lt=inactive_threshold) | Q(last_purchase__isnull=True),
        is_active=True
    )
    
    for customer in inactive_customers:
        # Vérifier qu'un rappel n'existe pas déjà
        existing_reminder = AutomatedReminder.objects.filter(
            customer=customer,
            reminder_type='inactive_customer',
            status__in=['pending', 'sent']
        ).exists()
        
        if not existing_reminder:
            AutomatedReminder.objects.create(
                pharmacie=customer.pharmacie,
                customer=customer,
                reminder_type='inactive_customer',
                message="Nous vous avons manqué ! Revenez découvrir nos nouveautés et promotions.",
                send_via_sms=True,
                send_via_email=True,
                scheduled_datetime=timezone.now() + timedelta(hours=1),
                status='pending'
            )


# ============================================================================
# CAMPAGNES MARKETING - STATISTIQUES EN TEMPS RÉEL
# ============================================================================

@receiver(post_save, sender='gestion_suivit.CampaignRecipient')
def update_campaign_statistics(sender, instance, **kwargs):
    """Met à jour les statistiques de la campagne en temps réel"""
    campaign = instance.campaign
    
    # Compter les statuts
    stats = campaign.recipients.aggregate(
        sent=Count('id', filter=Q(status__in=['sent', 'delivered', 'opened', 'clicked', 'converted'])),
        delivered=Count('id', filter=Q(status__in=['delivered', 'opened', 'clicked', 'converted'])),
        opened=Count('id', filter=Q(status='opened') | Q(status='clicked') | Q(status='converted')),
        clicked=Count('id', filter=Q(status='clicked') | Q(status='converted')),
        conversions=Count('id', filter=Q(converted=True))
    )
    
    campaign.total_sent = stats['sent']
    campaign.total_delivered = stats['delivered']
    campaign.total_opened = stats['opened']
    campaign.total_clicked = stats['clicked']
    campaign.total_conversions = stats['conversions']
    
    # Calculer le revenu généré
    revenue = campaign.recipients.filter(converted=True).aggregate(
        total=Sum('conversion_amount')
    )['total'] or Decimal('0.00')
    campaign.revenue_generated = revenue
    
    campaign.save(update_fields=[
        'total_sent', 'total_delivered', 'total_opened',
        'total_clicked', 'total_conversions', 'revenue_generated'
    ])


# ============================================================================
# SEGMENTATION AUTOMATIQUE DES CLIENTS
# ============================================================================

@receiver(post_save, sender='gestion_vente.Sale')
def trigger_segment_recalculation(sender, instance, **kwargs):
    """Déclenche le recalcul des segments dynamiques"""
    if instance.status == 'completed':
        # Marquer les segments dynamiques pour recalcul
        from .models import CustomerSegment
        
        segments = CustomerSegment.objects.filter(
            pharmacie=instance.customer.pharmacie,
            is_dynamic=True,
            is_active=True
        )
        
        for segment in segments:
            # Vérifier si le client correspond au segment
            if customer_matches_segment(instance.customer, segment):
                segment.customer_count = F('customer_count') + 1
                segment.last_calculated_at = timezone.now()
                segment.save()


def customer_matches_segment(customer, segment):
    """Vérifie si un client correspond aux critères d'un segment"""
    from datetime import date
    
    # Vérifier l'âge
    if segment.age_min or segment.age_max:
        if not customer.date_of_birth:
            return False
        
        age = (date.today() - customer.date_of_birth).days // 365
        
        if segment.age_min and age < segment.age_min:
            return False
        if segment.age_max and age > segment.age_max:
            return False
    
    # Vérifier le sexe
    if segment.gender and customer.gender != segment.gender:
        return False
    
    # Vérifier le nombre d'achats
    if segment.min_purchases:
        purchase_count = customer.sales.filter(status='completed').count()
        if purchase_count < segment.min_purchases:
            return False
    
    # Vérifier le montant dépensé
    if segment.min_amount_spent:
        total_spent = customer.sales.filter(
            status='completed'
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        
        if total_spent < segment.min_amount_spent:
            return False
    
    # Vérifier la ville
    if segment.city and customer.city != segment.city:
        return False
    
    # Vérifier le niveau de fidélité
    if segment.loyalty_tier:
        try:
            loyalty = customer.loyalty_account
            if loyalty.current_tier != segment.loyalty_tier:
                return False
        except:
            return False
    
    return True


# ============================================================================
# GESTION LEADS - ATTRIBUTION AUTOMATIQUE
# ============================================================================

@receiver(post_save, sender='gestion_suivit.Lead')
def auto_assign_lead(sender, instance, created, **kwargs):
    """Attribue automatiquement un lead à un utilisateur"""
    if created and not instance.assigned_to:
        from gestion_rh.models import Utilisateur
        
        # Trouver l'utilisateur avec le moins de leads actifs
        users = Utilisateur.objects.filter(
            pharmacie=instance.pharmacie,
            is_active=True,
            role__in=['manager', 'pharmacist']
        ).annotate(
            active_leads=Count('leads_assigned', filter=Q(leads_assigned__status__in=['new', 'contacted', 'qualified']))
        ).order_by('active_leads')
        
        if users.exists():
            instance.assigned_to = users.first()
            instance.save(update_fields=['assigned_to'])


@receiver(post_save, sender='gestion_suivit.Lead')
def convert_lead_to_customer(sender, instance, **kwargs):
    """Convertit un lead en client quand le statut passe à 'converted'"""
    if instance.status == 'converted' and not instance.converted_to_customer:
        from gestion_rh.models import Client
        
        # Créer le client
        client = Client.objects.create(
            pharmacie=instance.pharmacie,
            first_name=instance.first_name,
            last_name=instance.last_name,
            email=instance.email,
            phone=instance.phone,
            customer_type='individual'
        )
        
        instance.converted_to_customer = client
        instance.converted_at = timezone.now()
        instance.save(update_fields=['converted_to_customer', 'converted_at'])


# ============================================================================
# RECOMMANDATIONS IA - SUGGESTIONS PERSONNALISÉES
# ============================================================================

@receiver(post_save, sender='gestion_vente.Sale')
def generate_product_recommendations(sender, instance, **kwargs):
    """Génère des recommandations de produits après un achat"""
    if instance.status == 'completed':
        # Analyser l'historique d'achats
        recommendations = calculate_product_recommendations(
            customer=instance.customer,
            recent_purchase=instance
        )
        
        # Créer un rappel avec les recommandations
        if recommendations:
            from .models import AutomatedReminder
            
            products_list = ", ".join([p['name'] for p in recommendations[:3]])
            
            AutomatedReminder.objects.create(
                pharmacie=instance.customer.pharmacie,
                customer=instance.customer,
                reminder_type='other',
                message=f"Basé sur vos achats récents, nous vous recommandons : {products_list}",
                send_via_email=True,
                send_via_push=True,
                scheduled_datetime=timezone.now() + timedelta(days=7),
                status='pending'
            )


def calculate_product_recommendations(customer, recent_purchase):
    """
    Calcule des recommandations de produits basées sur l'IA
    Algorithme simple de collaborative filtering
    """
    from gestion_vente.models import Product, SaleItem
    
    # Produits achetés récemment
    recent_products = SaleItem.objects.filter(
        sale=recent_purchase
    ).values_list('product_id', flat=True)
    
    # Trouver des clients similaires (qui ont acheté les mêmes produits)
    similar_customers = SaleItem.objects.filter(
        product_id__in=recent_products,
        sale__status='completed'
    ).exclude(
        sale__customer=customer
    ).values('sale__customer').annotate(
        similarity_score=Count('product')
    ).order_by('-similarity_score')[:10]
    
    if not similar_customers:
        return []
    
    similar_customer_ids = [c['sale__customer'] for c in similar_customers]
    
    # Produits achetés par ces clients similaires
    recommended_products = SaleItem.objects.filter(
        sale__customer_id__in=similar_customer_ids,
        sale__status='completed'
    ).exclude(
        product_id__in=recent_products
    ).values('product__id', 'product__name').annotate(
        recommendation_score=Count('product')
    ).order_by('-recommendation_score')[:5]
    
    return list(recommended_products)


# ============================================================================
# ANALYSE PRÉDICTIVE DES BESOINS CLIENTS
# ============================================================================

def predict_customer_needs():
    """
    Fonction périodique (Celery/Cron)
    Prédit les besoins futurs des clients basés sur l'historique
    """
    from .models import Treatment, AutomatedReminder
    from gestion_vente.models import Sale, SaleItem
    
    # Analyser les achats réguliers (produits achetés périodiquement)
    regular_purchases = SaleItem.objects.filter(
        sale__status='completed'
    ).values('sale__customer', 'product').annotate(
        purchase_count=Count('id'),
        last_purchase=Max('sale__sale_date')
    ).filter(purchase_count__gte=3)  # Au moins 3 achats
    
    for purchase in regular_purchases:
        customer_id = purchase['sale__customer']
        product_id = purchase['product']
        last_purchase_date = purchase['last_purchase']
        
        # Calculer l'intervalle moyen entre achats
        purchases_dates = SaleItem.objects.filter(
            sale__customer_id=customer_id,
            product_id=product_id,
            sale__status='completed'
        ).order_by('sale__sale_date').values_list('sale__sale_date', flat=True)
        
        if len(purchases_dates) >= 2:
            intervals = []
            for i in range(1, len(purchases_dates)):
                interval = (purchases_dates[i] - purchases_dates[i-1]).days
                intervals.append(interval)
            
            avg_interval = sum(intervals) / len(intervals)
            
            # Prédire le prochain achat
            next_purchase_date = last_purchase_date + timedelta(days=int(avg_interval))
            
            # Créer un rappel 3 jours avant
            reminder_date = next_purchase_date - timedelta(days=3)
            
            if reminder_date > timezone.now().date():
                from gestion_rh.models import Client
                from gestion_vente.models import Product
                
                customer = Client.objects.get(id=customer_id)
                product = Product.objects.get(id=product_id)
                
                AutomatedReminder.objects.get_or_create(
                    pharmacie=customer.pharmacie,
                    customer=customer,
                    reminder_type='other',
                    scheduled_datetime=timezone.make_aware(
                        timezone.datetime.combine(reminder_date, timezone.datetime.min.time().replace(hour=10))
                    ),
                    defaults={
                        'message': f"Il est temps de renouveler votre {product.name}. Commandez dès maintenant !",
                        'send_via_sms': True,
                        'send_via_push': True,
                        'status': 'pending'
                    }
                )


# ============================================================================
# HELPERS
# ============================================================================

def calculate_customer_lifetime_value(customer):
    """Calcule la valeur vie client (CLV)"""
    from gestion_vente.models import Sale
    
    # Total dépensé
    total_spent = Sale.objects.filter(
        customer=customer,
        status='completed'
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    # Fréquence d'achat
    purchase_count = Sale.objects.filter(
        customer=customer,
        status='completed'
    ).count()
    
    # Durée de la relation
    first_purchase = Sale.objects.filter(
        customer=customer,
        status='completed'
    ).order_by('sale_date').first()
    
    if first_purchase:
        relationship_days = (timezone.now().date() - first_purchase.sale_date).days
        if relationship_days > 0:
            avg_purchase_per_year = (purchase_count / relationship_days) * 365
            avg_order_value = total_spent / purchase_count if purchase_count > 0 else Decimal('0.00')
            
            # CLV simplifié = avg order value × purchases per year × estimated years (5)
            clv = avg_order_value * Decimal(str(avg_purchase_per_year)) * 5
            return clv
    
    return total_spent
