from rest_framework import status, permissions, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, login
from django.shortcuts import render
from django.views.generic import TemplateView
from optometrist.models import Optometrist, Patient, EyeExamination  # Using the same user model and Patient model
from patients.models import OnlineSessionRequest
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

class DoctorDashboardPageView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'doctors/dashboard.html'
    login_url = '/doctor/api/login/'

    def test_func(self):
        return self.request.user.role == 'doctor'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Fetch examinations (referrals) assigned to this doctor
        context['examinations'] = EyeExamination.objects.filter(consultant=self.request.user).select_related('patient', 'optometrist').order_by('-created_at')
        
        # Pending session requests and accepted by this doctor
        # We'll just pass all session requests that are pending, or approved by this doctor
        from django.db.models import Q
        context['session_requests'] = OnlineSessionRequest.objects.filter(
            Q(status='pending') | Q(doctor=self.request.user)
        ).select_related('user').order_by('-created_at')
        
        return context

class LoginDoctor(APIView):
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        return render(request, 'doctors/login.html')
    
    def post(self, request):
        phone_number = request.data.get('phone_number')
        password = request.data.get('password')

        user = authenticate(phone_number=phone_number, password=password)

        if user:
            # Check if the user is a doctor
            if user.role != 'doctor':
                return Response({'error': 'Unauthorized. This portal is for doctors only.'}, status=status.HTTP_403_FORBIDDEN)
            
            # Log the user into the session (Built-in Auth support)
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
                    'role': user.role
                }
            })
        
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

from optometrist.serializers import OptometristProfileSerializer

class DoctorListView(generics.ListAPIView):
    queryset = Optometrist.objects.filter(role='doctor', is_active=True)
    serializer_class = OptometristProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

from django.shortcuts import get_object_or_404, redirect
from optometrist.models import EyeExamination, Medication

class AcceptAndConsultView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'doctors/consultation.html'
    login_url = '/doctor/api/login/'
    
    def test_func(self):
        return self.request.user.role == 'doctor'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        exam = get_object_or_404(EyeExamination, id=self.kwargs['pk'], consultant=self.request.user)
        context['exam'] = exam
        context['is_completed'] = exam.is_completed
        # Fetch patient history (past exams) for this patient by phone number
        context['past_exams'] = EyeExamination.objects.filter(
            patient__phone_number=exam.patient.phone_number
        ).exclude(id=exam.id).order_by('-created_at')

        # CMP (Chronic Management Program) clinical data for this patient, so the
        # doctor sees the full picture when the optometrist sends a CMP patient.
        from optometrist.models import CMPRecord
        patient = exam.patient
        if patient.phone_number:
            patient_records = Patient.objects.filter(phone_number=patient.phone_number)
        else:
            patient_records = Patient.objects.filter(pk=patient.pk)
        cmp_records = CMPRecord.objects.filter(
            patient__in=patient_records
        ).select_related('optometrist').order_by('-recorded_at')
        cmp_patient = patient_records.filter(is_cmp_patient=True).order_by('-created_at').first()
        context['cmp_patient'] = cmp_patient
        context['is_cmp_patient'] = cmp_patient is not None
        context['cmp_records'] = cmp_records
        context['cmp_latest'] = cmp_records.first()
        return context

    def dispatch(self, request, *args, **kwargs):
        # We allow viewing and updating even if completed
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        exam = get_object_or_404(EyeExamination, id=self.kwargs['pk'], consultant=self.request.user)
        
        # Update Patient Records if changed
        patient = exam.patient
        patient.name = request.POST.get('patient_name', patient.name)
        patient.age = request.POST.get('patient_age', patient.age)
        patient.gender = request.POST.get('patient_gender', patient.gender)
        patient.address = request.POST.get('patient_address', patient.address)
        patient.save()

        # Update Diagnosis Notes, Diagnosis and Advice
        exam.diagnosis_notes = request.POST.get('diagnosis_notes', '')
        exam.provisional_diagnosis = request.POST.get('provisional_diagnosis')
        exam.advice = request.POST.get('advice')
        exam.is_completed = True
        exam.save()

        # Handle Medications with all fields
        med_names = request.POST.getlist('med_name[]')
        if med_names:
            # Clear old medications if re-submitting
            exam.medications.all().delete()
            
            # Get all medication field arrays
            med_quantities = request.POST.getlist('med_quantity[]')
            med_frequencies = request.POST.getlist('med_frequency[]')
            med_eyes = request.POST.getlist('med_eye[]')
            med_durations = request.POST.getlist('med_duration[]')
            med_instructions_list = request.POST.getlist('med_instructions[]')
            
            # Create medication entries
            for i in range(len(med_names)):
                # Only create if name is provided
                if med_names[i].strip():
                    Medication.objects.create(
                        examination=exam,
                        name=med_names[i],
                        quantity=med_quantities[i] if i < len(med_quantities) else '',
                        frequency=med_frequencies[i] if i < len(med_frequencies) else '',
                        eye=med_eyes[i] if i < len(med_eyes) else 'Both eyes',
                        duration=med_durations[i] if i < len(med_durations) else '',
                        instructions=med_instructions_list[i] if i < len(med_instructions_list) else ''
                    )
        
        return redirect('doctor_dashboard')

from patients.views import CsrfExemptSessionAuth

from phase2.google_calendar_utils import create_meet_event

class ScheduleSessionView(APIView):
    authentication_classes = [CsrfExemptSessionAuth]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if request.user.role != 'doctor':
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
            
        session_request = get_object_or_404(OnlineSessionRequest, pk=pk)
        scheduled_time = request.data.get('scheduled_time')
        
        if not scheduled_time:
            return Response({'error': 'Time is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Automate Google Meet Link generation
        meet_link, error = create_meet_event(scheduled_time, summary=f"Eye Consultation with {session_request.user.name}")
        
        if error:
            # Fallback to manual link if provided, but the request says doctor just sends time/date
            # So if error, we probably need to alert
            return Response({'error': f'Failed to generate Google Meet link: {error}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        session_request.doctor = request.user
        session_request.scheduled_time = scheduled_time
        session_request.meet_link = meet_link
        session_request.status = 'approved'
        session_request.save()
        
        return Response({'status': 'success', 'message': 'Session scheduled successfully', 'meet_link': meet_link})
