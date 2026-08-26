from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import check_password
from .models import Optometrist
from .serializers import OptometristSerializer, OptometristProfileSerializer
from django.shortcuts import render
from django.views.generic import TemplateView

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

class OptometristDashboardPageView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'optometrist/dashboard.html'
    login_url = '/api/login/'

    def test_func(self):
        return self.request.user.role == 'optometrist'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['examinations'] = EyeExamination.objects.filter(optometrist=user).select_related('patient', 'consultant').order_by('-created_at')
        
        # Only corporate optometrists can see corporate data
        if user.designation == 'corporate':
            context['corporate_patients'] = Patient.objects.filter(login_type='corporate').order_by('-created_at')
            context['company_names'] = Patient.objects.filter(login_type='corporate').values_list('company_name', flat=True).distinct()
        else:
            context['corporate_patients'] = []
            context['company_names'] = []
        return context

class LandingPageView(TemplateView):
    template_name = 'optometrist/landing.html'

class RegisterOptometrist(generics.CreateAPIView):
    queryset = Optometrist.objects.all()
    serializer_class = OptometristSerializer
    permission_classes = [permissions.AllowAny]

from django.contrib.auth import authenticate, login

class LoginOptometrist(APIView):
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        return render(request, 'optometrist/login.html')
    
    def post(self, request):
        phone_number = request.data.get('phone_number')
        password = request.data.get('password')

        user = authenticate(phone_number=phone_number, password=password)

        if user:
            if user.role != 'optometrist':
                return Response({'error': 'Unauthorized. This portal is for optometrists only.'}, status=status.HTTP_403_FORBIDDEN)
            
            # Log user into session for TemplateView support
            login(request, user)
                
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': {
                    'id': user.id,
                    'name': user.name,
                    'phone_number': user.phone_number,
                    'email': user.email,
                    'role': user.role,
                    'designation': user.designation
                }
            })
        
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

class OptometristListView(generics.ListAPIView):
    queryset = Optometrist.objects.filter(is_active=True)
    serializer_class = OptometristProfileSerializer
    permission_classes = [permissions.AllowAny]

class OptometristDetailView(generics.RetrieveAPIView):
    queryset = Optometrist.objects.filter(is_active=True)
    serializer_class = OptometristProfileSerializer
    permission_classes = [permissions.AllowAny]

class OptometristProfileUpdateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.designation == 'corporate':
            return Response({'error': 'Unauthorized. Corporate profiles can only be updated by administrators.'}, status=status.HTTP_403_FORBIDDEN)
            
        serializer = OptometristSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CorporatePatientsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.designation != 'corporate':
            return Response({'error': 'Unauthorized. Only corporate optometrists can access this data.'}, status=status.HTTP_403_FORBIDDEN)
            
        company_name = request.query_params.get('company_name')
        patients = Patient.objects.filter(login_type='corporate')
        
        if company_name:
            patients = patients.filter(company_name=company_name)
            
        serializer = PatientSerializer(patients, many=True)
        return Response(serializer.data)

from .models import Patient, EyeExamination
from .serializers import PatientSerializer, EyeExaminationSerializer

class EyeExaminationCreateAPIView(generics.CreateAPIView):
    queryset = EyeExamination.objects.all()
    serializer_class = EyeExaminationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Assign the logged-in optometrist
        serializer.save(optometrist=self.request.user)

class EyeExaminationDetailView(generics.RetrieveUpdateAPIView):
    queryset = EyeExamination.objects.all()
    serializer_class = EyeExaminationSerializer
    permission_classes = [permissions.IsAuthenticated]

class ExaminationByPhoneView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, phone_number):
        exam = EyeExamination.objects.filter(patient__phone_number=phone_number, is_completed=False).order_by('-created_at').first()
        if not exam:
            return Response({"detail": "No pending examination found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = EyeExaminationSerializer(exam)
        return Response(serializer.data)

class PatientHistoryAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, phone_number):
        exams = EyeExamination.objects.filter(patient__phone_number=phone_number).order_by('-created_at')
        data = []
        for e in exams:
            data.append({
                "id": e.id,
                "date": e.created_at.strftime("%d %M %Y"),
                "consultant": e.consultant.name if e.consultant else "N/A",
                "diagnosis": e.provisional_diagnosis or "Pending...",
                "is_completed": e.is_completed
            })
        return Response(data)
        return Response({'message': 'No pending examination found'}, status=404)

class PatientInfoByPhoneView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, phone_number):
        patient = Patient.objects.filter(phone_number=phone_number).first()
        if not patient:
            return Response({"detail": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = PatientSerializer(patient)
        return Response(serializer.data)

class NewExaminationPageView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'optometrist/new_examination.html'
    login_url = '/api/login/'

    def test_func(self):
        return self.request.user.role == 'optometrist'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['doctors'] = Optometrist.objects.filter(role='doctor', is_active=True)
        return context


# ============ CMP (Chronic Management Program) Clinical Data ============

from decimal import Decimal, InvalidOperation
from .models import CMPRecord


def _to_decimal(val):
    """Parse a decimal field, treating blanks/invalid input as None."""
    if val is None or val == '':
        return None
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _to_bool_or_none(val):
    """Parse a Yes/No field. Blank/unknown -> None, otherwise truthy strings -> True."""
    if val in (None, '', 'unknown'):
        return None
    return val in (True, 'true', 'yes', 'on', '1', 1)


def _serialize_cmp_record(record, request=None):
    def file_url(f):
        if not f:
            return None
        return request.build_absolute_uri(f.url) if request else f.url

    return {
        'id': record.id,
        'cmp_type': record.cmp_type,
        'cmp_type_display': record.get_cmp_type_display(),
        'recorded_at': record.recorded_at.strftime('%d %b %Y, %H:%M'),
        'optometrist': record.optometrist.name if record.optometrist else 'N/A',
        # Diabetic
        'hba1c_value': str(record.hba1c_value) if record.hba1c_value is not None else None,
        'hba1c_report': file_url(record.hba1c_report),
        'kft_report': file_url(record.kft_report),
        'diabetes_type': record.diabetes_type,
        'diabetes_type_display': record.get_diabetes_type_display() if record.diabetes_type else None,
        'current_diabetes_medications': record.current_diabetes_medications,
        'has_kidney_disease': record.has_kidney_disease,
        'exercise_frequency': record.exercise_frequency,
        # Pediatric Myopia
        'school_grade': record.school_grade,
        'axial_length': str(record.axial_length) if record.axial_length is not None else None,
        'dilated_refraction': str(record.dilated_refraction) if record.dilated_refraction is not None else None,
        'avg_daily_screen_time': str(record.avg_daily_screen_time) if record.avg_daily_screen_time is not None else None,
        'avg_daily_outdoor_time': str(record.avg_daily_outdoor_time) if record.avg_daily_outdoor_time is not None else None,
        'eye_muscle_status': record.eye_muscle_status,
        'notes': record.notes,
    }


class CMPRecordPageView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Optometrist-only page to record CMP clinical data for a patient."""
    template_name = 'optometrist/cmp_record.html'
    login_url = '/api/login/'

    def test_func(self):
        return self.request.user.role == 'optometrist'


class CMPRecordCreateAPIView(APIView):
    """Create a new (append-only) CMP clinical record. Optometrist only.

    A new row is created on every save so previous values are preserved for
    progression tracking — existing records are never overwritten.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.role != 'optometrist':
            return Response({'error': 'Only optometrists can record CMP clinical data.'},
                            status=status.HTTP_403_FORBIDDEN)

        patient_id = request.data.get('patient_id')
        phone = request.data.get('phone_number')

        patient = None
        if patient_id:
            patient = Patient.objects.filter(id=patient_id).first()
        if not patient and phone:
            patient = Patient.objects.filter(phone_number=phone).order_by('-created_at').first()
        if not patient:
            return Response({'error': 'Patient not found. Provide a valid phone number.'},
                            status=status.HTTP_404_NOT_FOUND)

        cmp_type = request.data.get('cmp_type') or patient.cmp_type
        valid_cmp_types = {c[0] for c in Patient.CMP_TYPE_CHOICES}
        if cmp_type not in valid_cmp_types:
            return Response({'error': 'A valid CMP type is required.'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Enroll / sync the patient's CMP tag if the optometrist is confirming it here
        tag_updates = []
        if not patient.is_cmp_patient:
            patient.is_cmp_patient = True
            tag_updates.append('is_cmp_patient')
        if patient.cmp_type != cmp_type:
            patient.cmp_type = cmp_type
            tag_updates.append('cmp_type')
        if tag_updates:
            patient.save(update_fields=tag_updates)

        record = CMPRecord(
            patient=patient,
            optometrist=request.user,
            cmp_type=cmp_type,
            # Diabetic CMP fields
            hba1c_value=_to_decimal(request.data.get('hba1c_value')),
            diabetes_type=request.data.get('diabetes_type') or None,
            current_diabetes_medications=request.data.get('current_diabetes_medications') or None,
            has_kidney_disease=_to_bool_or_none(request.data.get('has_kidney_disease')),
            exercise_frequency=request.data.get('exercise_frequency') or None,
            # Pediatric Myopia CMP fields
            school_grade=request.data.get('school_grade') or None,
            axial_length=_to_decimal(request.data.get('axial_length')),
            dilated_refraction=_to_decimal(request.data.get('dilated_refraction')),
            avg_daily_screen_time=_to_decimal(request.data.get('avg_daily_screen_time')),
            avg_daily_outdoor_time=_to_decimal(request.data.get('avg_daily_outdoor_time')),
            eye_muscle_status=request.data.get('eye_muscle_status') or None,
            notes=request.data.get('notes') or None,
        )
        if 'hba1c_report' in request.FILES:
            record.hba1c_report = request.FILES['hba1c_report']
        if 'kft_report' in request.FILES:
            record.kft_report = request.FILES['kft_report']
        record.save()

        return Response(
            {'status': 'success', 'message': 'CMP clinical record saved.', 'record_id': record.id},
            status=status.HTTP_201_CREATED
        )


class CMPHistoryByPhoneView(APIView):
    """Return a patient's full CMP clinical history (latest first)."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, phone_number):
        patients = Patient.objects.filter(phone_number=phone_number)
        patient = patients.order_by('-created_at').first()
        records = CMPRecord.objects.filter(patient__in=patients).order_by('-recorded_at')
        return Response({
            'patient': {
                'name': patient.name if patient else None,
                'phone_number': phone_number,
                'is_cmp_patient': patient.is_cmp_patient if patient else False,
                'cmp_type': patient.cmp_type if patient else None,
                'cmp_type_display': patient.get_cmp_type_display() if patient and patient.cmp_type else None,
            },
            'count': records.count(),
            'records': [_serialize_cmp_record(r, request) for r in records],
        })
