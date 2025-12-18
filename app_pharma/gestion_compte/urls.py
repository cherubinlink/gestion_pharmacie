from django.urls import path
from gestion_compte import views

app_name = 'gestion_compte'


urlpatterns = [
    
    
     # Authentification
    path('inscription/', views.inscription_view, name='inscription'),
    path('connexion/', views.connexion_view, name='connexion'),
    path('deconnexion/', views.deconnexion_view, name='deconnexion'),
    
    
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
