from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import Optometrist

class OptometristCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Optometrist
        fields = (
            'phone_number', 'name', 'email', 'role', 'license_number', 
            'qualification', 'specialization', 'experience_years', 'bio', 
            'clinic_address', 'profile_picture', 'website', 'office_hours', 
            'languages', 'is_active', 'is_staff', 'is_superuser', 'groups', 
            'user_permissions'
        )

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if Optometrist.objects.filter(phone_number=phone_number).exists():
            raise forms.ValidationError("Phone number already exists.")
        return phone_number

class OptometristChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = Optometrist
        fields = '__all__'
