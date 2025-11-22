
from django.contrib import admin
from django.urls import path
from django.http import HttpResponse
from django.urls import include, path


def home(request):
    return HttpResponse("<h1>Assistente Financeiro <h1>")

urlpatterns = [
    path('', home),
    path('admin/', admin.site.urls),
    path('whatsapp', include('whatsapp.urls')),
]
