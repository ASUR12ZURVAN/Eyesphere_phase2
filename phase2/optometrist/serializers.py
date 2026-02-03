from rest_framework import serializers
from .models import Optometrist
from django.contrib.auth.hashers import make_password

class OptometristSerializer(serializers.ModelSerializer):
    class Meta:
        model = Optometrist
        fields = [
            'id', 'name', 'phone_number', 'password', 'email',
            'license_number', 'qualification', 'specialization', 'experience_years',
            'bio', 'clinic_address', 'profile_picture', 'website', 'office_hours', 'languages'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'id': {'read_only': True}
        }

    def create(self, validated_data):
        return Optometrist.objects.create_user(**validated_data)

class OptometristProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Optometrist
        exclude = ['password']
        read_only_fields = ['id', 'email', 'license_number', 'created_at', 'updated_at']
