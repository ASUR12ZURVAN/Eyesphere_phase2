from rest_framework import status, permissions, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, login
from django.shortcuts import render
from django.views.generic import TemplateView
from optometrist.models import Optometrist, Patient, EyeExamination  # Using the same user model and Patient model
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
        return context

    def dispatch(self, request, *args, **kwargs):
        exam = get_object_or_404(EyeExamination, id=self.kwargs['pk'], consultant=self.request.user)
        if exam.is_completed:
            return redirect('doctor_dashboard')
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        exam = get_object_or_404(EyeExamination, id=self.kwargs['pk'], consultant=self.request.user)
        
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

