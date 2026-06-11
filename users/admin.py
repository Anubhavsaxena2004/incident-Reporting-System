from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ('username', 'email', 'role', 'phone_number', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('System Authorization Details', {'fields': ('role', 'phone_number')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('System Authorization Details', {'fields': ('role', 'phone_number')}),
    )


admin.site.register(User, CustomUserAdmin)
