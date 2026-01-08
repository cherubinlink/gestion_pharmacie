from django.shortcuts import render

# Create your views here.



# =========== messages ==============
def message(request):
    return render(request,'gestion_communication/message.html')
