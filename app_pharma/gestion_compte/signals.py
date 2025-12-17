from django.db.models.signals import post_save,pre_save
from django.dispatch import receiver
from django.utils import timezone
from gestion_compte.models import (
    Utilisateur, ProfilUtilisateur, Pharmacie, Role, 
    MembrePharmacie, HistoriqueModificationPharmacie
)
import uuid




# ==================== SIGNALS ====================

@receiver(post_save, sender=Utilisateur)
def creer_pharmacie_pour_nouveau_proprietaire(sender, instance, created, **kwargs):
    if created and not instance.is_superuser:
        numero_autorisation_unique = f"TMP-{uuid.uuid4().hex[:8].upper()}"

        pharmacie = Pharmacie.objects.create(
            nom_commercial=f"Pharmacie de {instance.get_full_name()}",
            adresse="À compléter",
            ville="À compléter",
            telephone_principal=instance.telephone or "+237000000000",
            email=instance.email,
            numero_autorisation=numero_autorisation_unique,
            proprietaire=instance
        )

        role_proprietaire, _ = Role.objects.get_or_create(
            code='proprietaire',
            defaults={'nom': 'Propriétaire'}
        )

        MembrePharmacie.objects.create(
            utilisateur=instance,
            pharmacie=pharmacie,
            role=role_proprietaire,
            statut='actif'
        )

        instance.pharmacie_active = pharmacie
        instance.save(update_fields=['pharmacie_active'])


@receiver(post_save, sender=Utilisateur)
def creer_profil_utilisateur(sender, instance, created, **kwargs):
    if created:
        ProfilUtilisateur.objects.create(utilisateur=instance)


@receiver(post_save, sender=Utilisateur)
def sauvegarder_profil(sender, instance, **kwargs):
    """
    Signal pour sauvegarder le profil quand l'utilisateur est modifié
    """
    if hasattr(instance, 'profil'):
        instance.profil.save()


@receiver(pre_save, sender=Pharmacie)
def tracer_modifications_pharmacie(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        ancienne = Pharmacie.objects.only(
            'nom_commercial', 'adresse', 'telephone_principal',
            'email', 'numero_autorisation', 'statut'
        ).get(pk=instance.pk)
    except Pharmacie.DoesNotExist:
        return

    champs_a_tracer = [
        'nom_commercial', 'adresse', 'telephone_principal',
        'email', 'numero_autorisation', 'statut'
    ]

    for champ in champs_a_tracer:
        ancienne_valeur = getattr(ancienne, champ)
        nouvelle_valeur = getattr(instance, champ)

        if ancienne_valeur != nouvelle_valeur:
            HistoriqueModificationPharmacie.objects.create(
                pharmacie=instance,
                utilisateur=getattr(instance, '_utilisateur_modificateur', None),
                champ_modifie=champ,
                ancienne_valeur=str(ancienne_valeur),
                nouvelle_valeur=str(nouvelle_valeur)
            )



