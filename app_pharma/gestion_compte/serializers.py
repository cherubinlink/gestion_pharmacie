from rest_framework import serializers
from gestion_compte.models import Utilisateur, ProfilUtilisateur, Pharmacie, MembrePharmacie

class UtilisateurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Utilisateur
        fields = ['id', 'email', 'first_name', 'last_name', 'telephone', 'statut', 'date_creation']
        read_only_fields = ['id', 'date_creation']


class ProfilUtilisateurSerializer(serializers.ModelSerializer):
    utilisateur = UtilisateurSerializer(read_only=True)
    
    class Meta:
        model = ProfilUtilisateur
        fields = '__all__'


class PharmacieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pharmacie
        fields = '__all__'
        read_only_fields = ['id', 'code', 'proprietaire', 'date_creation']


class MembrePharmacieSerializer(serializers.ModelSerializer):
    utilisateur = UtilisateurSerializer(read_only=True)
    pharmacie = PharmacieSerializer(read_only=True)
    
    class Meta:
        model = MembrePharmacie
        fields = '__all__'