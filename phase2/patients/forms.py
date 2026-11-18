import re

from django import forms
from django.utils import timezone


class PatientRegistrationForm(forms.Form):
    name = forms.CharField(max_length=200, label="Full name")
    date_of_birth = forms.DateField(
        label="Date of birth",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    gender = forms.ChoiceField(
        choices=[
            ("male", "Male"),
            ("female", "Female"),
            ("other", "Other"),
        ]
    )
    phone_number = forms.CharField(max_length=25, label="Contact number")
    email = forms.EmailField()
    address = forms.CharField(
        label="Residential address",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    diabetes = forms.TypedChoiceField(
        label="Are you diabetic?",
        choices=[("false", "No"), ("true", "Yes")],
        coerce=lambda value: value == "true",
        widget=forms.RadioSelect,
    )

    def clean_phone_number(self):
        phone_number = self.cleaned_data["phone_number"]
        normalized = re.sub(r"[\s()-]", "", phone_number)
        if not re.fullmatch(r"\+?[0-9]{7,15}", normalized):
            raise forms.ValidationError("Enter a valid phone number with 7 to 15 digits.")
        return normalized

    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data["date_of_birth"]
        if date_of_birth > timezone.localdate():
            raise forms.ValidationError("Date of birth cannot be in the future.")
        return date_of_birth
