from django.urls import path
from gestion_rh import views

app_name = 'gestion_rh'


urlpatterns = [
    
    # controle
    path('parametre_controle/',views.parametre_controle, name='parametre-controle'),
    
]
