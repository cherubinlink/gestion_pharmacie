from django.db.models.signals import post_save
from django.dispatch import receiver
from gestion_compte.models import Utilisateur,Pharmacie,MembrePharmacie,Role,ProfilUtilisateur




# ==================== SIGNALS ====================

@receiver(post_save, sender=Utilisateur)
def creer_pharmacie_pour_nouveau_proprietaire(sender, instance, created, **kwargs):
    """
    Signal pour créer automatiquement une pharmacie lors de la création d'un compte propriétaire
    """
    if created and not instance.is_superuser:
        # Créer une pharmacie par défaut
        pharmacie = Pharmacie.objects.create(
            nom_commercial=f"Pharmacie de {instance.get_full_name()}",
            adresse="À compléter",
            ville="À compléter",
            telephone_principal=instance.telephone or "À compléter",
            email=instance.email,
            numero_autorisation="À compléter",
            proprietaire=instance
        )
        
        # Créer le rôle de propriétaire
        role_proprietaire, _ = Role.objects.get_or_create(
            code='proprietaire',
            defaults={'nom': 'Propriétaire', 'description': 'Propriétaire de la pharmacie'}
        )
        
        # Ajouter l'utilisateur comme membre propriétaire
        MembrePharmacie.objects.create(
            utilisateur=instance,
            pharmacie=pharmacie,
            role=role_proprietaire,
            statut='actif'
        )
        
        # Définir cette pharmacie comme active
        instance.pharmacie_active = pharmacie
        instance.save(update_fields=['pharmacie_active'])


@receiver(post_save, sender=Utilisateur)
def gerer_creation_utilisateur(sender, instance, created, **kwargs):
    """
    Signal pour gérer la création automatique du profil et de la pharmacie
    """
    if created:
        # 1. Créer le profil utilisateur automatiquement
        ProfilUtilisateur.objects.create(utilisateur=instance)
        
        # 2. Si ce n'est pas un superuser, créer une pharmacie
        if not instance.is_superuser:
            # Créer une pharmacie par défaut
            pharmacie = Pharmacie.objects.create(
                nom_commercial=f"Pharmacie de {instance.get_full_name()}",
                adresse="À compléter",
                ville="À compléter",
                telephone_principal=instance.telephone or "À compléter",
                email=instance.email,
                numero_autorisation="À compléter",
                proprietaire=instance
            )
            
            # Créer le rôle de propriétaire
            role_proprietaire, _ = Role.objects.get_or_create(
                code='proprietaire',
                defaults={
                    'nom': 'Propriétaire',
                    'description': 'Propriétaire de la pharmacie'
                }
            )
            
            # Ajouter l'utilisateur comme membre propriétaire
            MembrePharmacie.objects.create(
                utilisateur=instance,
                pharmacie=pharmacie,
                role=role_proprietaire,
                statut='actif'
            )
            
            # Définir cette pharmacie comme active
            instance.pharmacie_active = pharmacie
            instance.save(update_fields=['pharmacie_active'])


@receiver(post_save, sender=Utilisateur)
def sauvegarder_profil(sender, instance, **kwargs):
    """
    Signal pour sauvegarder le profil quand l'utilisateur est modifié
    """
    if hasattr(instance, 'profil'):
        instance.profil.save()

