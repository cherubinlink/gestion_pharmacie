from django.urls import path
from gestion_communication import views

app_name = 'gestion_communication'



urlpatterns = [
    # message
    path('message/',views.message, name='message'),
]
