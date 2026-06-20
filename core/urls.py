
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from dashboard.views import login_view, cadastro_view

def home(request):
    return HttpResponse("<h1>Assistente Financeiro</h1>")

urlpatterns = [
    path('', home),
    path('admin/', admin.site.urls),
    path('whatsapp/', include('whatsapp.urls')),  
    path('api/', include('transactions.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('login/', login_view, name='login'),
    path('cadastro/', cadastro_view, name='cadastro'),
]

