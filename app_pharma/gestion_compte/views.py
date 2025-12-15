from django.shortcuts import render

# Create your views here.



def dashboard(request):
    return render(request,'gestion_compte/dashboard.html')


def analyse(request):
    return render(request,'gestion_compte/analyse.html')


def parametre_compte(request):
    return render(request,'gestion_compte/parametre_compte.html')

def voir_profile(request):
    return render(request,'gestion_compte/voir_profile.html')
