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
                    'role': user.role
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

from .models import Patient, EyeExamination
from .serializers import PatientSerializer, EyeExaminationSerializer

class EyeExaminationCreateAPIView(generics.CreateAPIView):
    queryset = EyeExamination.objects.all()
    serializer_class = EyeExaminationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Assign the logged-in optometrist
        serializer.save(optometrist=self.request.user)

class NewExaminationPageView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'optometrist/new_examination.html'
    login_url = '/api/login/'

    def test_func(self):
        return self.request.user.role == 'optometrist'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['doctors'] = Optometrist.objects.filter(role='doctor', is_active=True)
        return context
