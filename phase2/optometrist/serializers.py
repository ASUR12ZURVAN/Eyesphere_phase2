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
    risk_factor = serializers.CharField(write_only=True, required=False)
    
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
        
        # Extract patient fields validation data
        name = validated_data.pop('name', None)
        age = validated_data.pop('age', 0)
        gender = validated_data.pop('gender', 'Other')
        phone = validated_data.pop('phone_number', '')
        addr = validated_data.pop('address', '')
        risk_factor = validated_data.pop('risk_factor', 'low')
        
        # Patient Handling - Track by phone number
        patient = None
        if phone:
            patient = Patient.objects.filter(phone_number=phone).first()
            if patient:
                # Update existing patient info
                patient.name = name or patient.name
                patient.age = age or patient.age
                patient.gender = gender or patient.gender
                patient.address = addr or patient.address
                patient.risk_factor = risk_factor or patient.risk_factor
                patient.save()
        
        if not patient and name:
            # Create new patient
            patient = Patient.objects.create(
                name=name,
                age=age,
                gender=gender,
                phone_number=phone,
                address=addr,
                risk_factor=risk_factor
            )
        
        if not patient:
            # Check if patient_id was provided (from PrimaryKeyRelatedField source='patient')
            patient = validated_data.get('patient')
            
        if not patient:
            raise serializers.ValidationError({"error": "Patient must be provided or created (phone number or name is required)."})
            
        validated_data['patient'] = patient
        
        # Consultant Handling
        consultant = validated_data.get('consultant')
        if not consultant:
            # Fallback: Auto-assign a doctor (Consultant)
            doctor = Optometrist.objects.filter(role='doctor', is_active=True).first()
            if doctor:
                validated_data['consultant'] = doctor
                consultant = doctor
            else:
                 raise serializers.ValidationError({"error": "No available doctor to assign."})
        
        # Check if an examination for this patient already exists for this doctor and is not completed
        # The prompt says "if it had previously been sent to doctor then replace it with updated one"
        # We'll update the existing one if it exists.
        existing_exam = EyeExamination.objects.filter(patient=patient, consultant=consultant, is_completed=False).first()
        
        if existing_exam:
            # Update existing exam
            for attr, value in validated_data.items():
                setattr(existing_exam, attr, value)
            existing_exam.save()
            exam = existing_exam
            # Clear old medications as they will be re-added
            exam.medications.all().delete()
        else:
            # Create New Exam
            exam = EyeExamination.objects.create(**validated_data)
        
        # Create Medications
        for med_data in medications_data:
            Medication.objects.create(examination=exam, **med_data)
            
        return exam
