from django.contrib import admin
from .models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("name", "phone_number", "created_at", "updated_at", "time_zone", "locale")
    search_fields = ("name", "phone_number", "locale")
