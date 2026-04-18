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
from .models import ScreeningTestResult, OnlineSessionRequest, RedeemableService, RedemptionTicket, HomeTestRequest
import json
from django.shortcuts import redirect
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.views import View
from django.http import HttpResponse

class CsrfExemptSessionAuth(SessionAuthentication):
    """Skip CSRF check for session auth — our templates already send X-CSRFToken header."""
    def enforce_csrf(self, request):
        return  # Skip CSRF enforcement since we handle it via JS headers


class RegisterPatient(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return render(request, 'patients/register.html')

    def post(self, request):
        name = request.data.get('name')
        phone_number = request.data.get('phone_number')
        email = request.data.get('email')
        password = request.data.get('password')
        age = request.data.get('age')
        gender = request.data.get('gender')
        address = request.data.get('address')
        login_type = request.data.get('login_type', 'at_home')
        company_name = request.data.get('company_name')
        designation = request.data.get('designation')

        if not name or not phone_number or not password or not age or not gender:
            return Response({'error': 'Name, phone number, password, age, and gender are required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        if login_type == 'corporate' and not company_name:
             return Response({'error': 'Company name is required for corporate login.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if phone number already registered
        if Optometrist.objects.filter(phone_number=phone_number).exists():
            return Response({'error': 'This phone number is already registered.'}, status=status.HTTP_400_BAD_REQUEST)

        # Create patient user account for login
        user = Optometrist.objects.create_user(
            phone_number=phone_number,
            name=name,
            password=password,
            email=email if email else None,
            role='patient'
        )
        
        # Create actual Patient record in the database
        Patient.objects.create(
            name=name,
            phone_number=phone_number,
            age=age,
            gender=gender,
            address=address,
            login_type=login_type,
            company_name=company_name if login_type == 'corporate' else None,
            designation=designation if login_type == 'corporate' else None
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
        
        # Redemption data
        context['redeemable_services'] = RedeemableService.objects.all()
        context['my_tickets'] = RedemptionTicket.objects.filter(user=user).select_related('service').order_by('-redeemed_at')
        
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


class PatientLogoutView(APIView):
    authentication_classes = [CsrfExemptSessionAuth]
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        logout(request)
        return Response({'status': 'success', 'message': 'Logged out successfully'})
    
    def get(self, request):
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
        return render(request, 'patients/pdf_screening.html', context)


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
        return render(request, 'patients/pdf_exam.html', context)


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


class UpdatePatientProfileView(APIView):
    authentication_classes = [CsrfExemptSessionAuth]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.role != 'patient':
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
            
        try:
            # Handle both JSON and Form data
            data = request.data if isinstance(request.data, dict) else json.loads(request.body)
            email = data.get('email')
            age = data.get('age')
            gender = data.get('gender')
            address = data.get('address')
            login_type = data.get('login_type')
            company_name = data.get('company_name')
            designation = data.get('designation')
            
            user = request.user
            
            # 1. Update user auth table (email only)
            if email is not None:
                # Check if email is already taken by another user
                from django.db.models import Q
                if Optometrist.objects.filter(email=email).exclude(pk=user.pk).exists():
                    return Response({'error': 'This email address is already in use by another account.'}, status=status.HTTP_400_BAD_REQUEST)
                
                user.email = email
                user.save(update_fields=['email'])
                
            # 2. Update/Create patient demographic table
            patient_record = Patient.objects.filter(phone_number=user.phone_number).order_by('-created_at').first()
            
            if not patient_record:
                patient_record = Patient.objects.create(
                    name=user.name,
                    phone_number=user.phone_number,
                    age=int(age) if age and age != '' else 0,
                    gender=gender if gender and gender != '' else 'other',
                    address=address if address else '',
                    login_type=login_type if login_type else 'at_home',
                    company_name=company_name if login_type == 'corporate' else None,
                    designation=designation if login_type == 'corporate' else None
                )
            else:
                update_fields = []
                if age is not None and age != '':
                    try:
                        patient_record.age = int(age)
                        update_fields.append('age')
                    except ValueError:
                        return Response({'error': 'Invalid age format.'}, status=status.HTTP_400_BAD_REQUEST)
                        
                if gender is not None and gender != '':
                    patient_record.gender = gender
                    update_fields.append('gender')
                if address is not None:
                    patient_record.address = address
                    update_fields.append('address')
                
                if login_type:
                    patient_record.login_type = login_type
                    update_fields.append('login_type')
                    if login_type == 'corporate':
                        if company_name:
                            patient_record.company_name = company_name
                            update_fields.append('company_name')
                        if designation is not None:
                            patient_record.designation = designation
                            update_fields.append('designation')
                    else:
                        patient_record.company_name = None
                        patient_record.designation = None
                        update_fields.extend(['company_name', 'designation'])
                
                if update_fields:
                    patient_record.save(update_fields=update_fields)

            # 3. Reward logic
            if patient_record and not patient_record.has_received_reward:
                if user.email and patient_record.age > 0 and patient_record.gender and patient_record.address:
                    user.coins += 100
                    user.save(update_fields=['coins'])
                    patient_record.has_received_reward = True
                    patient_record.save(update_fields=['has_received_reward'])
                
            return Response({'status': 'success', 'message': 'Profile updated successfully'})

        except Exception as e:
            return Response({'error': f'An unexpected error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RedeemServiceView(APIView):
    authentication_classes = [CsrfExemptSessionAuth]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            data = request.data if isinstance(request.data, dict) else json.loads(request.body)
            service_id = data.get('service_id')
            
            if not service_id:
                return Response({'error': 'Service ID is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            service = get_object_or_404(RedeemableService, id=service_id)
            user = request.user
            
            if user.coins < service.coins_required:
                return Response({
                    'error': f'Insufficient coins. You need {service.coins_required} coins, but you only have {user.coins}.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Atomic transaction to ensure coin deduction and ticket creation
            from django.db import transaction
            with transaction.atomic():
                # Deduct coins
                user.coins -= service.coins_required
                user.save(update_fields=['coins'])
                
                # Create ticket
                ticket = RedemptionTicket.objects.create(
                    user=user,
                    service=service
                )
                
            return Response({
                'status': 'success',
                'message': f'Successfully redeemed {service.name}!',
                'ticket_code': ticket.ticket_code,
                'remaining_coins': user.coins
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetOptometristsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        optometrists = Optometrist.objects.filter(role='optometrist', is_active=True)
        data = [{'id': o.id, 'name': o.name} for o in optometrists]
        return Response(data)

class GetPatientProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        patient_record = Patient.objects.filter(phone_number=user.phone_number).first()
        return Response({
            'phone_number': user.phone_number,
            'email': user.email,
            'company_name': patient_record.company_name if patient_record else None,
            'address': patient_record.address if patient_record else ""
        })

class BookHomeTestView(APIView):
    authentication_classes = [CsrfExemptSessionAuth]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            data = request.data if isinstance(request.data, dict) else json.loads(request.body)
            optometrist_id = data.get('optometrist_id')
            address = data.get('address')
            
            if not optometrist_id or not address:
                return Response({'error': 'Optometrist and address are required.'}, status=status.HTTP_400_BAD_REQUEST)
            
            if optometrist_id == 'auto':
                # Pick a random active optometrist
                import random
                optometrists = Optometrist.objects.filter(role='optometrist', is_active=True)
                if not optometrists.exists():
                    return Response({'error': 'No available optometrists at the moment.'}, status=status.HTTP_400_BAD_REQUEST)
                optometrist = random.choice(optometrists)
            else:
                optometrist = get_object_or_404(Optometrist, id=optometrist_id, role='optometrist')
            
            # Fetch patient record for company name
            patient_record = Patient.objects.filter(phone_number=request.user.phone_number).first()
            company_name = patient_record.company_name if patient_record else None

            HomeTestRequest.objects.create(
                user=request.user,
                optometrist=optometrist,
                phone_number=request.user.phone_number,
                email=request.user.email,
                company_name=company_name,
                address=address
            )
            
            return Response({'status': 'success', 'message': 'Home test booked successfully!'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
