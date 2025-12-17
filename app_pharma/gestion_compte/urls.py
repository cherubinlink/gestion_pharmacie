from django.urls import path
from gestion_compte import views

app_name = 'gestion_compte'


urlpatterns = [
    
    
     # Authentification
    path('inscription/', views.inscription_view, name='inscription'),
    path('connexion/', views.connexion_view, name='connexion'),
    path('deconnexion/', views.deconnexion_view, name='deconnexion'),
    
    # Tableau de bord
    path('tableau-bord/', views.tableau_bord_view, name='tableau_bord'),
    
    
     # Vue principale (lecture seule - Onglet 1)
    path('parametres/', views.parametres_compte_view, name='parametres_compte'),
    
    # Onglet 2: Profil personnel
    path('parametres/profil/', views.modifier_profil_personnel_view, name='modifier_profil_personnel'),
    
    # Onglet 3: Configuration pharmacie
    path('parametres/pharmacie/', views.configuration_pharmacie_view, name='configuration_pharmacie'),
    
    # Onglet 4: Planning
    path('parametres/planning/', views.planning_view, name='planning'),
    
    # Onglet 5: Gestion membres
    path('parametres/membres/', views.gestion_membres_view, name='gestion_membres'),
    
    # Onglet 6: Préférences
    path('parametres/preferences/', views.preferences_view, name='preferences'),
    
    # Actions complémentaires
    path('parametres/changer-pharmacie/<uuid:pharmacie_id>/', views.changer_pharmacie_active_view, name='changer_pharmacie_active'),
    path('parametres/retirer-membre/<uuid:membre_id>/', views.retirer_membre_view, name='retirer_membre'),
   
    
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
