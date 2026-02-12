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

from .models import Patient, EyeExamination, Medication

class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = '__all__'

class MedicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medication
        fields = ['name', 'quantity', 'frequency', 'eye', 'duration', 'instructions']

class EyeExaminationSerializer(serializers.ModelSerializer):
    medications = MedicationSerializer(many=True, required=False)
    patient = PatientSerializer(read_only=True)
    patient_id = serializers.PrimaryKeyRelatedField(
        queryset=Patient.objects.all(), source='patient', write_only=True, required=False
    )
    # Fields to create new patient inline
    name = serializers.CharField(write_only=True, required=False)
    age = serializers.IntegerField(write_only=True, required=False)
    gender = serializers.CharField(write_only=True, required=False)
    phone_number = serializers.CharField(write_only=True, required=False)
    address = serializers.CharField(write_only=True, required=False)
    
    # Consultant selection
    consultant_id = serializers.PrimaryKeyRelatedField(
        queryset=Optometrist.objects.filter(role='doctor'), source='consultant', write_only=True, required=False
    )

    class Meta:
        model = EyeExamination
        fields = '__all__'
        read_only_fields = ['optometrist', 'date_of_visit', 'consultant']

    def create(self, validated_data):
        medications_data = validated_data.pop('medications', [])
        
        # Patient Handling
        patient = validated_data.pop('patient', None)
        
        # Extract patient fields validation data
        name = validated_data.pop('name', None)
        age = validated_data.pop('age', 0)
        gender = validated_data.pop('gender', 'Other')
        phone = validated_data.pop('phone_number', '')
        addr = validated_data.pop('address', '')
        
        if not patient and name:
            # Create new patient
            patient = Patient.objects.create(
                name=name,
                age=age,
                gender=gender,
                phone_number=phone,
                address=addr
            )
        
        if not patient:
            raise serializers.ValidationError("Patient must be provided or created (name is required).")
            
        validated_data['patient'] = patient
        
        # Consultant Handling
        # If consultant_id was passed, it's already validated and put into validated_data key 'consultant' by source='consultant'
        if 'consultant' not in validated_data:
            # Fallback: Auto-assign a doctor (Consultant)
            doctor = Optometrist.objects.filter(role='doctor', is_active=True).first()
            if doctor:
                validated_data['consultant'] = doctor
            else:
                 # Optional: Raise error if no doctor available and none selected
                 pass
        
        # Create Exam
        exam = EyeExamination.objects.create(**validated_data)
        
        # Create Medications
        for med_data in medications_data:
            Medication.objects.create(examination=exam, **med_data)
            
        return exam
