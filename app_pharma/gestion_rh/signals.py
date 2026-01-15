"""
Signals pour automatiser les processus métier
"""
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.conf import settings
import secrets
import string
from decimal import Decimal
from datetime import datetime, timedelta

from gestion_rh.models import (
     Employee, Client, LeaveRequest, WorkSchedule,
    TimeEntry, WorkSession, EmployeeTransferHistory,
    ClientTransferHistory, PerformanceMetrics, AbsenceRecord
)
from gestion_compte.models import Utilisateur


def generate_temporary_password(length=12):
    """Génère un mot de passe temporaire sécurisé"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for i in range(length))
    return password


def send_temporary_password_email(user, password):
    """Envoie le mot de passe temporaire par email"""
    subject = "Votre compte a été créé"
    message = f"""
    Bonjour {user.get_full_name()},
    
    Votre compte a été créé avec succès.
    
    Nom d'utilisateur: {user.username}
    Mot de passe temporaire: {password}
    
    Veuillez changer ce mot de passe lors de votre première connexion.
    
    Cordialement,
    L'équipe
    """
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=True,
    )


@receiver(post_save, sender=Utilisateur)
def handle_new_user_creation(sender, instance, created, **kwargs):
    if not created:
        return

    temp_password = generate_temporary_password()

    Utilisateur.objects.filter(pk=instance.pk).update(
        password=make_password(temp_password)
    )

    send_temporary_password_email(instance, temp_password)


@receiver(post_save, sender=Employee)
def create_employee_id(sender, instance, created, **kwargs):
    """
    Génère un ID employé unique lors de la création
    """
    if created and not instance.employee_id:
        # Format: PHARM-YYYY-XXXX
        year = timezone.now().year
        count = Employee.objects.filter(
            pharmacy=instance.pharmacy,
            created_at__year=year
        ).count()
        
        instance.employee_id = f"EMP-{instance.pharmacy.license_number[:4]}-{year}-{count:04d}"
        instance.save(update_fields=['employee_id'])


@receiver(post_save, sender=Client)
def create_client_number(sender, instance, created, **kwargs):
    """
    Génère un numéro client unique lors de la création
    """
    if created and not instance.client_number:
        year = timezone.now().year
        count = Client.objects.filter(
            pharmacy=instance.pharmacy,
            created_at__year=year
        ).count()
        
        instance.client_number = f"CLT-{instance.pharmacy.license_number[:4]}-{year}-{count:04d}"
        instance.save(update_fields=['client_number'])


@receiver(pre_save, sender=Employee)
def track_employee_transfer(sender, instance, **kwargs):
    """
    Enregistre l'historique lors du transfert d'un employé
    """
    if instance.pk:
        try:
            old_instance = Employee.objects.get(pk=instance.pk)
            
            # Vérifier si la pharmacie a changé
            if old_instance.pharmacy != instance.pharmacy:
                EmployeeTransferHistory.objects.create(
                    employee=instance,
                    from_pharmacy=old_instance.pharmacy,
                    to_pharmacy=instance.pharmacy,
                    reason="Transfert",
                    old_salary=old_instance.salary,
                    new_salary=instance.salary,
                    transferred_by=None  # À définir dans la vue
                )
        except Employee.DoesNotExist:
            pass


@receiver(pre_save, sender=Client)
def track_client_transfer(sender, instance, **kwargs):
    """
    Enregistre l'historique lors du transfert d'un client
    """
    if instance.pk:
        try:
            old_instance = Client.objects.get(pk=instance.pk)
            
            # Vérifier si la pharmacie a changé
            if old_instance.pharmacy != instance.pharmacy:
                ClientTransferHistory.objects.create(
                    client=instance,
                    from_pharmacy=old_instance.pharmacy,
                    to_pharmacy=instance.pharmacy,
                    reason="Transfert",
                    loyalty_points_transferred=instance.loyalty_points,
                    transferred_by=None  # À définir dans la vue
                )
        except Client.DoesNotExist:
            pass


@receiver(post_save, sender=LeaveRequest)
def update_schedule_on_leave_approval(sender, instance, created, **kwargs):
    """
    Met à jour automatiquement le planning lors de l'approbation d'un congé
    """
    if not created and instance.status == 'approved':
        # Supprimer les horaires planifiés pendant la période de congé
        WorkSchedule.objects.filter(
            employee=instance.employee,
            date__gte=instance.start_date,
            date__lte=instance.end_date
        ).delete()


@receiver(post_save, sender=TimeEntry)
def create_or_update_work_session(sender, instance, created, **kwargs):
    """
    Crée ou met à jour une session de travail basée sur les pointages
    """
    if instance.entry_type == 'clock_in':
        # Vérifier s'il existe déjà une session pour ce jour
        session, created = WorkSession.objects.get_or_create(
            employee=instance.employee,
            date=instance.timestamp.date(),
            defaults={
                'clock_in': instance,
                'scheduled_start': instance.timestamp.time(),
                'scheduled_end': instance.timestamp.time(),  # À définir
            }
        )
        
        # Vérifier si c'est un retard
        if hasattr(instance.employee, 'work_schedules'):
            schedule = instance.employee.work_schedules.filter(
                date=instance.timestamp.date()
            ).first()
            
            if schedule:
                session.scheduled_start = schedule.start_time
                session.scheduled_end = schedule.end_time
                
                # Calculer le retard
                scheduled_datetime = datetime.combine(
                    instance.timestamp.date(),
                    schedule.start_time
                )
                if instance.timestamp.time() > schedule.start_time:
                    late_delta = instance.timestamp - scheduled_datetime.replace(
                        tzinfo=instance.timestamp.tzinfo
                    )
                    session.is_late = True
                    session.late_duration = int(late_delta.total_seconds() / 60)
                
                session.save()
    
    elif instance.entry_type == 'clock_out':
        # Mettre à jour la session existante
        try:
            session = WorkSession.objects.get(
                employee=instance.employee,
                date=instance.timestamp.date(),
                is_complete=False
            )
            session.clock_out = instance
            session.is_complete = True
            
            # Calculer les heures travaillées
            time_diff = instance.timestamp - session.clock_in.timestamp
            session.actual_hours = Decimal(str(time_diff.total_seconds() / 3600))
            
            # Calculer les heures supplémentaires
            scheduled_hours = Decimal('8.0')  # Par défaut, à calculer depuis le schedule
            if session.actual_hours > scheduled_hours:
                session.overtime_hours = session.actual_hours - scheduled_hours
            
            session.save()
            
        except WorkSession.DoesNotExist:
            pass


@receiver(post_save, sender=WorkSession)
def detect_absence(sender, instance, created, **kwargs):
    """
    Détecte automatiquement les absences basées sur les sessions de travail
    """
    # Si une session n'a pas de clock_out après la fin prévue
    if not instance.is_complete:
        scheduled_end = datetime.combine(
            instance.date,
            instance.scheduled_end
        )
        
        if timezone.now() > scheduled_end + timedelta(hours=1):
            # Créer un enregistrement d'absence si non existant
            AbsenceRecord.objects.get_or_create(
                employee=instance.employee,
                date=instance.date,
                defaults={
                    'absence_type': 'unauthorized',
                    'scheduled_start': instance.scheduled_start,
                    'scheduled_end': instance.scheduled_end,
                    'actual_start': instance.clock_in.timestamp.time() if instance.clock_in else None,
                    'duration_minutes': 0,
                    'reason': 'Absence non justifiée détectée automatiquement',
                }
            )


@receiver(post_save, sender=AbsenceRecord)
def send_absence_alert(sender, instance, created, **kwargs):
    """
    Envoie une alerte en cas d'absence ou de retard
    """
    if created and instance.absence_type in ['unauthorized', 'late']:
        # Envoyer une notification au responsable
        # (À implémenter avec votre système de notification)
        pass


def calculate_performance_metrics(employee, period_start, period_end):
    """
    Calcule les métriques de performance pour un employé
    """
    # Calculer la ponctualité
    total_sessions = WorkSession.objects.filter(
        employee=employee,
        date__gte=period_start,
        date__lte=period_end
    ).count()
    
    late_sessions = WorkSession.objects.filter(
        employee=employee,
        date__gte=period_start,
        date__lte=period_end,
        is_late=True
    ).count()
    
    punctuality_rate = Decimal('100.00')
    if total_sessions > 0:
        punctuality_rate = Decimal(str((1 - late_sessions / total_sessions) * 100))
    
    # Calculer la présence
    total_scheduled = WorkSchedule.objects.filter(
        employee=employee,
        date__gte=period_start,
        date__lte=period_end
    ).count()
    
    absences = AbsenceRecord.objects.filter(
        employee=employee,
        date__gte=period_start,
        date__lte=period_end,
        absence_type='unauthorized'
    ).count()
    
    attendance_rate = Decimal('100.00')
    if total_scheduled > 0:
        attendance_rate = Decimal(str((1 - absences / total_scheduled) * 100))
    
    # Créer ou mettre à jour les métriques
    PerformanceMetrics.objects.update_or_create(
        employee=employee,
        period_start=period_start,
        period_end=period_end,
        defaults={
            'punctuality_rate': punctuality_rate,
            'attendance_rate': attendance_rate,
        }
    )


# Signal pour calculer les métriques mensuellement
# (À déclencher via une tâche Celery ou cron)
