from django.urls import path
from gestion_compte import views

app_name = 'gestion_compte'


urlpatterns = [
    
    
    # Authentification
    # Inscription
    path('inscription/', views.inscription_view, name='inscription'),
    path('inscription/ajax/', views.inscription_ajax_view, name='inscription_ajax'),
    
    # Vérifications disponibilité
    path('verifier/email/', views.verifier_email_disponible, name='verifier_email'),
    path('verifier/username/', views.verifier_username_disponible, name='verifier_username'),
    
    # Activation compte
    path('activer/<str:token>/', views.activer_compte_view, name='activer_compte'),
    
    # Statistiques (admin)
    path('stats/inscriptions/', views.statistiques_inscriptions_view, name='stats_inscriptions'),
    
        # 1. Connexion principale (GET/POST)
    path('connexion/', views.connexion_view, name='connexion'),
    
    # 2. Connexion AJAX (POST)
    path('connexion/ajax/', views.connexion_ajax_view, name='connexion-ajax'),
    
    # 3. Statistiques connexions (GET, admin only)
    path('admin/stats/connexions/', views.statistiques_connexions_view,  name='stats-connexions'),
    
    # ========== DÉCONNEXION (4 URLs) ==========
    
    # 1. Déconnexion principale
    path('deconnexion/', views.deconnexion_view, name='deconnexion'),
    
    # 2. Déconnexion AJAX
    path('deconnexion/ajax/', views.deconnexion_ajax_view, name='deconnexion-ajax'),
    
    # 3. Déconnexion tous appareils
    path('deconnexion/tous-appareils/', views.deconnexion_tous_appareils_view, name='deconnexion-tous-appareils'),
    
    # 4. Statistiques déconnexions (admin)
    path('admin/stats/deconnexions/', views.statistiques_deconnexions_view, name='stats-deconnexions'),

    
    
     # ==================== DASHBOARD ====================
    path('', views.dashboard, name='dashboard'),
    
    # ==================== PHARMACIE ====================
    # Liste et création
    path('pharmacies/', views.pharmacie_liste, name='pharmacie_liste'),
    path('pharmacies/creer/', views.pharmacie_creer, name='pharmacie_creer'),
    
    # Détails et modification
    path('pharmacies/<uuid:pharmacie_id>/', views.pharmacie_detail, name='pharmacie_detail'),
    path('pharmacies/<uuid:pharmacie_id>/modifier/', views.pharmacie_modifier, name='pharmacie_modifier'),
    
    # Actions sur pharmacie
    path('pharmacies/<uuid:pharmacie_id>/changer-statut/', views.pharmacie_changer_statut, name='pharmacie_changer_statut'),
    path('pharmacies/<uuid:pharmacie_id>/selectionner/', views.pharmacie_selectionner, name='pharmacie_selectionner'),
    
    # AJAX
    path('pharmacies/<uuid:pharmacie_id>/completion/', views.pharmacie_completion_ajax, name='pharmacie_completion_ajax'),
    
    # ==================== UTILISATEURS ====================
    # Liste et création
    path('utilisateurs/', views.utilisateur_liste, name='utilisateur_liste'),
    path('utilisateurs/creer/', views.utilisateur_creer, name='utilisateur_creer'),
    
    # Détails et modification
    path('utilisateurs/<uuid:utilisateur_id>/', views.utilisateur_detail, name='utilisateur_detail'),
    path('utilisateurs/<uuid:utilisateur_id>/modifier/', views.utilisateur_modifier, name='utilisateur_modifier'),
    
    # Actions sur utilisateur
    path('utilisateurs/<uuid:utilisateur_id>/changer-statut/', views.utilisateur_changer_statut, name='utilisateur_changer_statut'),
    path('utilisateurs/<uuid:utilisateur_id>/reinitialiser-tentatives/', views.utilisateur_reinitialiser_tentatives, name='utilisateur_reinitialiser_tentatives'),
    
    # AJAX
    path('utilisateurs/stats/', views.utilisateur_stats_ajax, name='utilisateur_stats_ajax'),
    
    # ==================== PROFIL PERSONNEL ====================
    path('mon-profil/', views.mon_profil, name='mon_profil'),
    path('mon-profil/modifier/', views.mon_profil_modifier, name='mon_profil_modifier'),
    
    # ==================== PARAMÈTRES ====================
    path('parametres/', views.parametres_compte, name='parametres_compte'),
    
  
    

     # parametre
    path('parametre/',views.parametre_compte,name='parametre_compte'),
    
    # dashboard
    path('',views.dashboard,name='dashboard'),
    
    # analyse
    path('analyse/', views.analyse,name='analyse'),
    
    # parametre
    path('parametre/',views.parametre_compte,name='parametre_compte'),
    
    # voir profile
    path('voir_profil/',views.voir_profile,name='voir-profile'),
    
    # confidentialite
    path('centre_confidentialite/',views.centre_confidentialite,name='centre-confidentialite'),
    

]
