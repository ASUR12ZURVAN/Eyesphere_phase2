from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, login
from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from optometrist.models import Optometrist, Patient, EyeExamination


class RegisterPatient(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return render(request, 'patients/register.html')

    def post(self, request):
        name = request.data.get('name')
        phone_number = request.data.get('phone_number')
        email = request.data.get('email')
        password = request.data.get('password')

        if not name or not phone_number or not password:
            return Response({'error': 'Name, phone number and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if phone number already registered
        if Optometrist.objects.filter(phone_number=phone_number).exists():
            return Response({'error': 'This phone number is already registered.'}, status=status.HTTP_400_BAD_REQUEST)

        # Create patient user
        user = Optometrist.objects.create_user(
            phone_number=phone_number,
            name=name,
            password=password,
            email=email if email else None,
            role='patient'
        )

        return Response({
            'message': 'Account created successfully!',
            'user': {
                'id': user.id,
                'name': user.name,
                'phone_number': user.phone_number,
            }
        }, status=status.HTTP_201_CREATED)


class LoginPatient(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return render(request, 'patients/login.html')

    def post(self, request):
        phone_number = request.data.get('phone_number')
        password = request.data.get('password')

        user = authenticate(phone_number=phone_number, password=password)

        if user:
            if user.role != 'patient':
                return Response({'error': 'Unauthorized. This portal is for patients only.'}, status=status.HTTP_403_FORBIDDEN)

            # Log user into session
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


class PatientDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'patients/dashboard.html'
    login_url = '/patient/api/login/'

    def test_func(self):
        return self.request.user.role == 'patient'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Find patient records matching the logged-in user's phone number
        patient_records = Patient.objects.filter(phone_number=user.phone_number)

        # Fetch all examinations for those patient records, with related data
        examinations = EyeExamination.objects.filter(
            patient__in=patient_records
        ).select_related(
            'patient', 'optometrist', 'consultant'
        ).prefetch_related(
            'medications'
        ).order_by('-created_at')

        context['patient_records'] = patient_records
        context['examinations'] = examinations
        return context
