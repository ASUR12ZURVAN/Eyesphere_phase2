from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import check_password
from .models import Optometrist
from .serializers import OptometristSerializer, OptometristProfileSerializer
from django.views.generic import TemplateView

class OptometristLoginPageView(TemplateView):
    template_name = 'optometrist/login.html'

class OptometristRegisterPageView(TemplateView):
    template_name = 'optometrist/register.html'

class OptometristDashboardPageView(TemplateView):
    template_name = 'optometrist/dashboard.html'

class RegisterOptometrist(generics.CreateAPIView):
    queryset = Optometrist.objects.all()
    serializer_class = OptometristSerializer
    permission_classes = [permissions.AllowAny]

from django.contrib.auth import authenticate

class LoginOptometrist(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        phone_number = request.data.get('phone_number')
        password = request.data.get('password')

        user = authenticate(phone_number=phone_number, password=password)

        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': {
                    'id': user.id,
                    'name': user.name,
                    'phone_number': user.phone_number,
                    'email': user.email
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
