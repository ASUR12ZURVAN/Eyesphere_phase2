from django.contrib import admin
from .models import Optometrist, Patient, EyeExamination, Medication
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .forms import OptometristCreationForm, OptometristChangeForm

class MedicationInline(admin.TabularInline):
    model = Medication
    extra = 1

@admin.register(EyeExamination)
class EyeExaminationAdmin(admin.ModelAdmin):
    list_display = ('patient', 'optometrist', 'consultant', 'date_of_visit')
    list_filter = ('date_of_visit', 'optometrist', 'consultant')
    search_fields = ('patient__name', 'optometrist__name', 'provisional_diagnosis')
    inlines = [MedicationInline]

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('name', 'age', 'gender', 'phone_number', 'created_at')
    list_filter = ('gender', 'created_at')
    search_fields = ('name', 'phone_number')

@admin.register(Optometrist)
class OptometristAdmin(BaseUserAdmin):
    form = OptometristChangeForm
    add_form = OptometristCreationForm
    
    list_display = ('name', 'phone_number', 'role', 'email', 'license_number', 'is_active', 'is_staff', 'created_at')
    list_filter = ('role', 'is_active', 'is_staff', 'specialization', 'created_at')
    search_fields = ('name', 'phone_number', 'email', 'license_number', 'qualification')
    ordering = ('-created_at',)
    
    # UserAdmin specific fields
    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ('Role & Access', {'fields': ('role',)}),
        ('Personal Information', {'fields': ('name', 'email', 'profile_picture', 'languages', 'bio')}),
        ('Professional Details', {'fields': ('license_number', 'qualification', 'specialization', 'experience_years', 'clinic_address', 'website', 'office_hours')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    readonly_fields = ('created_at', 'updated_at', 'last_login')
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'name', 'password1', 'password2', 'role', 'is_staff', 'is_active'),
        }),
        ('Personal Information', {
            'fields': ('email', 'profile_picture', 'languages', 'bio'),
        }),
        ('Professional Details', {
            'fields': ('license_number', 'qualification', 'specialization', 'experience_years', 'clinic_address', 'website', 'office_hours'),
        }),
        ('Permissions', {
            'fields': ('is_superuser', 'groups', 'user_permissions'),
        }),
    )
