from django.test import TestCase, Client
from django.urls import reverse
from .models import Utilisateur, Pharmacie, ProfilUtilisateur

# Create your tests here.


class UtilisateurTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = Utilisateur.objects.create_user(
            email='test@test.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
    
    def test_creation_utilisateur(self):
        """Test de création d'utilisateur"""
        self.assertEqual(self.user.email, 'test@test.com')
        self.assertTrue(self.user.check_password('testpass123'))
    
    def test_creation_profil_automatique(self):
        """Test que le profil est créé automatiquement"""
        self.assertTrue(hasattr(self.user, 'profil'))
        self.assertIsInstance(self.user.profil, ProfilUtilisateur)
    
    def test_connexion(self):
        """Test de connexion"""
        response = self.client.post(reverse('gestion_compte:connexion'), {
            'username': 'test@test.com',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)  # Redirection
    
    def test_acces_tableau_bord_sans_connexion(self):
        """Test d'accès au tableau de bord sans être connecté"""
        response = self.client.get(reverse('gestion_compte:tableau_bord'))
        self.assertEqual(response.status_code, 302)  # Redirection vers login


class PharmacieTestCase(TestCase):
    def setUp(self):
        self.user = Utilisateur.objects.create_user(
            email='pharmacien@test.com',
            password='testpass123',
            first_name='Pharmacien',
            last_name='Test'
        )
        self.pharmacie = self.user.pharmacie_active
    
    def test_creation_pharmacie_automatique(self):
        """Test que la pharmacie est créée automatiquement"""
        self.assertIsNotNone(self.pharmacie)
        self.assertEqual(self.pharmacie.proprietaire, self.user)
    
    def test_generation_code_pharmacie(self):
        """Test que le code de pharmacie est généré"""
        self.assertTrue(self.pharmacie.code.startswith('PH'))
    
    def test_calcul_completion_pharmacie(self):
        """Test du calcul de complétion"""
        completion = self.pharmacie.calculer_completion()
        self.assertGreaterEqual(completion, 0)
        self.assertLessEqual(completion, 100)
