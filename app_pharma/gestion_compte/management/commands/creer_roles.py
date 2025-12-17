from django.core.management.base import BaseCommand
from gestion_compte.models import Role, PermissionSysteme, RolePermission



class Command(BaseCommand):
    help = 'Créer les rôles et permissions par défaut'

    def handle(self, *args, **options):
        # Créer les rôles
        roles_data = [
            {
                'code': 'proprietaire',
                'nom': 'Propriétaire',
                'description': 'Propriétaire de la pharmacie avec tous les droits'
            },
            {
                'code': 'administrateur',
                'nom': 'Administrateur',
                'description': 'Administrateur avec droits de gestion'
            },
            {
                'code': 'pharmacien',
                'nom': 'Pharmacien',
                'description': 'Pharmacien avec accès complet aux fonctions métier'
            },
            {
                'code': 'caissier',
                'nom': 'Caissier',
                'description': 'Caissier avec accès aux ventes'
            },
            {
                'code': 'gestionnaire_stock',
                'nom': 'Gestionnaire de stock',
                'description': 'Gestion des stocks et approvisionnements'
            },
        ]
        
        for role_data in roles_data:
            role, created = Role.objects.get_or_create(
                code=role_data['code'],
                defaults={
                    'nom': role_data['nom'],
                    'description': role_data['description']
                }
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Rôle créé: {role.nom}')
                )
        
        # Créer les permissions
        permissions_data = [
            {'code': 'ventes.creer', 'nom': 'Créer une vente', 'module': 'Ventes'},
            {'code': 'ventes.modifier', 'nom': 'Modifier une vente', 'module': 'Ventes'},
            {'code': 'ventes.supprimer', 'nom': 'Supprimer une vente', 'module': 'Ventes'},
            {'code': 'stock.voir', 'nom': 'Voir le stock', 'module': 'Stock'},
            {'code': 'stock.modifier', 'nom': 'Modifier le stock', 'module': 'Stock'},
            {'code': 'utilisateurs.gerer', 'nom': 'Gérer les utilisateurs', 'module': 'Utilisateurs'},
        ]
        
        for perm_data in permissions_data:
            perm, created = PermissionSysteme.objects.get_or_create(
                code=perm_data['code'],
                defaults={
                    'nom': perm_data['nom'],
                    'module': perm_data['module']
                }
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Permission créée: {perm.nom}')
                )
        
        self.stdout.write(self.style.SUCCESS('✅ Rôles et permissions créés avec succès'))