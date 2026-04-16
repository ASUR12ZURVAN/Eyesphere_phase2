from rest_framework import status, permissions
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from optometrist.models import Optometrist, Patient, EyeExamination
from .models import ScreeningTestResult, OnlineSessionRequest
import json
from django.shortcuts import redirect
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.views import View
from django.http import HttpResponse
from .utils import render_to_pdf

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
            
            # Reward daily login coins
            today = timezone.now().date()
            if not user.last_coin_login_date or user.last_coin_login_date < today:
                user.coins += 5
                user.last_coin_login_date = today
                user.save()

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

        # Daily Login Coin Check
        today = timezone.localdate()
        if user.last_coin_login_date != today:
            user.coins += 10
            user.last_coin_login_date = today
            user.save(update_fields=['coins', 'last_coin_login_date'])

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

        # Fetch screening test results for this user
        screening_results = ScreeningTestResult.objects.filter(user=user).order_by('-created_at')

        context['patient_records'] = patient_records
        context['examinations'] = examinations
        context['screening_results'] = screening_results
        context['session_requests'] = OnlineSessionRequest.objects.filter(user=user).order_by('-created_at')
        return context


# ============ Screening Test Page Views ============

class PatientTestMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = '/patient/api/login/'

    def test_func(self):
        return self.request.user.role == 'patient'


class VisionTestView(PatientTestMixin, TemplateView):
    template_name = 'patients/vision_test.html'


class ColorBlindTestView(PatientTestMixin, TemplateView):
    template_name = 'patients/color_blind_test.html'


class OSDITestView(PatientTestMixin, TemplateView):
    template_name = 'patients/osdi_test.html'


class BlinkTestView(PatientTestMixin, TemplateView):
    template_name = 'patients/blink_test.html'


# ============ API to Save Screening Results ============

class CsrfExemptSessionAuth(SessionAuthentication):
    """Skip CSRF check for session auth — our templates already send X-CSRFToken header."""
    def enforce_csrf(self, request):
        return  # Skip CSRF enforcement since we handle it via JS headers


class SaveScreeningResultView(APIView):
    authentication_classes = [CsrfExemptSessionAuth]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            data = request.data if isinstance(request.data, dict) else json.loads(request.body)
            test_type = data.get('test_type', '')
            result_data = data.get('result_data', {})
            score = data.get('score', '')

            if test_type not in ['vision', 'colorblind', 'dryeye', 'blink']:
                return Response({'status': 'error', 'message': 'Invalid test type'}, status=status.HTTP_400_BAD_REQUEST)

            ScreeningTestResult.objects.create(
                user=request.user,
                test_type=test_type,
                result_data=result_data,
                score=score,
            )
            
            # Reward test coins (20 coins max once every 3 days)
            today = timezone.now().date()
            user = request.user
            if not user.last_coin_test_date or user.last_coin_test_date <= today - timedelta(days=3):
                user.coins += 20
                user.last_coin_test_date = today
                user.save()

            return Response({'status': 'success', 'message': 'Result saved successfully!'})
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def patient_logout(request):
    logout(request)
    return redirect('patient_login_page')

class RequestOnlineSessionView(APIView):
    authentication_classes = [CsrfExemptSessionAuth]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            OnlineSessionRequest.objects.create(
                user=request.user,
                status='pending'
            )
            return Response({'status': 'success', 'message': 'approval request sent'})
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ============ PDF Download Views ============

class DownloadScreeningPDFView(LoginRequiredMixin, View):
    login_url = '/patient/api/login/'
    
    def get(self, request, pk):
        result = get_object_or_404(ScreeningTestResult, pk=pk)
        
        # Verify permissions: Optometrist/Doctor or the matching patient
        if request.user.role == 'patient' and result.user != request.user:
            return HttpResponse("Unauthorized", status=403)
            
        context = {
            'result': result,
        }
        pdf = render_to_pdf('patients/pdf_screening.html', context)
        if pdf:
            response = pdf
            response['Content-Disposition'] = f'attachment; filename="screening_report_{result.id}.pdf"'
            return response
        return HttpResponse("Failed to generate PDF.", status=500)


class DownloadExamPDFView(LoginRequiredMixin, View):
    login_url = '/patient/api/login/'
    
    def get(self, request, pk):
        exam = get_object_or_404(EyeExamination, pk=pk)
        
        # Verify permissions: Optometrist/Doctor or the matching patient
        if request.user.role == 'patient' and exam.patient.phone_number != request.user.phone_number:
            return HttpResponse("Unauthorized", status=403)
            
        context = {
            'exam': exam,
        }
        pdf = render_to_pdf('patients/pdf_exam.html', context)
        if pdf:
            response = pdf
            response['Content-Disposition'] = f'attachment; filename="exam_prescription_{exam.id}.pdf"'
            return response
        return HttpResponse("Failed to generate PDF.", status=500)


# ============ Retention Time Tracking ============

class UpdateRetentionTimeView(APIView):
    """
    Receives the number of seconds the user has been active and
    adds it cumulatively to their retention_time field.
    Called periodically (heartbeat) and on page unload via sendBeacon.
    """
    authentication_classes = [CsrfExemptSessionAuth]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            data = request.data if isinstance(request.data, dict) else json.loads(request.body)
            elapsed = int(data.get('elapsed_seconds', 0))
            if elapsed > 0:
                user = request.user
                # Use F() expression for safe concurrent updates
                from django.db.models import F
                Optometrist.objects.filter(pk=user.pk).update(
                    retention_time=F('retention_time') + elapsed
                )
            return Response({'status': 'ok'})
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


