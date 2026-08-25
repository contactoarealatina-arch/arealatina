from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'first_name', 'last_name', 'email', 'rol', 'telefono', 'is_active')
    list_filter = ('rol', 'is_active', 'is_staff')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'rut')
    ordering = ('first_name', 'last_name')

    fieldsets = UserAdmin.fieldsets + (
        ('Datos Area Latina', {'fields': ('rol', 'telefono', 'rut')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Datos Area Latina', {'fields': ('first_name', 'last_name', 'email', 'rol', 'telefono', 'rut')}),
    )
