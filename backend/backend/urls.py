from django.contrib import admin
from django.urls import path
from financeiro.views import criar_transacao

urlpatterns = [
    path('admin/', admin.site.urls),
    path('transacao/', criar_transacao),
]
