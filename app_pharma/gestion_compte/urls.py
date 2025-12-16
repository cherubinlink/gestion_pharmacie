from django.urls import path
from gestion_compte import views

app_name = 'gestion_compte'


urlpatterns = [
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
    
    # connexion
    path('connexion/',views.connexion,name='connexion'),
    
    # register
    path('register/',views.register,name='register'),
]
