from django.contrib import admin
from .models import Transacao, Category

# Configuração para visualizar as Transações
@admin.register(Transacao)
class TransacaoAdmin(admin.ModelAdmin):
    # O que vai aparecer nas colunas da lista
    list_display = ('id', 'description', 'value', 'type', 'category', 'date_transaction')
    
    # Filtros laterais para facilitar a busca
    list_filter = ('type', 'date_transaction', 'category')
    
    # Campo de busca
    search_fields = ('description',)

# Configuração para visualizar as Categorias
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)