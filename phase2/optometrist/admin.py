from django.contrib import admin
from .models import Optometrist
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

@admin.register(Optometrist)
class OptometristAdmin(BaseUserAdmin):
    list_display = ('name', 'phone_number', 'email', 'license_number', 'is_active', 'is_staff', 'created_at')
    list_filter = ('is_active', 'is_staff', 'specialization', 'created_at')
    search_fields = ('name', 'phone_number', 'email', 'license_number', 'qualification')
    ordering = ('-created_at',)
    
    # UserAdmin specific fields
    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ('Personal Information', {'fields': ('name', 'email', 'profile_picture', 'languages', 'bio')}),
        ('Professional Details', {'fields': ('license_number', 'qualification', 'specialization', 'experience_years', 'clinic_address', 'website', 'office_hours')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    readonly_fields = ('created_at', 'updated_at', 'last_login')
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'name', 'password', 'is_staff', 'is_active'),
        }),
    )
