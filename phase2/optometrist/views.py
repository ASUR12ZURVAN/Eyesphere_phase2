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
        context['examinations'] = EyeExamination.objects.filter(optometrist=self.request.user).select_related('patient', 'consultant').order_by('-created_at')
        context['corporate_patients'] = Patient.objects.filter(login_type='corporate').order_by('-created_at')
        # Get unique company names for filtering
        context['company_names'] = Patient.objects.filter(login_type='corporate').values_list('company_name', flat=True).distinct()
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

class OptometristProfileUpdateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        serializer = OptometristSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CorporatePatientsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
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
