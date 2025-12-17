from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from gestion_compte.models import (
    UtilisateurManager, Utilisateur, Pharmacie, ProfilUtilisateur,
    Role, RolePermission, PermissionSysteme, MembrePharmacie,
    HistoriqueConnexion, HistoriqueModificationPharmacie
)
from gestion_compte.serializers import (
    UtilisateurSerializer, ProfilUtilisateurSerializer, PharmacieSerializer
)


class UtilisateurViewSet(viewsets.ReadOnlyModelViewSet):
    """API pour les utilisateurs"""
    queryset = Utilisateur.objects.all()
    serializer_class = UtilisateurSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Récupérer l'utilisateur connecté"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class PharmacieViewSet(viewsets.ModelViewSet):
    """API pour les pharmacies"""
    queryset = Pharmacie.objects.all()
    serializer_class = PharmacieSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtrer les pharmacies de l'utilisateur"""
        return Pharmacie.objects.filter(
            membres__utilisateur=self.request.user,
            membres__statut='actif'
        ).distinct()