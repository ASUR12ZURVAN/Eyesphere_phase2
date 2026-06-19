from rest_framework import status, permissions
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from optometrist.models import Optometrist, Patient, EyeExamination, CMPRecord
from .models import ScreeningTestResult, OnlineSessionRequest, RedeemableService, RedemptionTicket, HomeTestRequest, PatientQuery
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

        # CMP onboarding identification (patient self-declared)
        is_cmp_patient = request.data.get('is_cmp_patient') in (True, 'true', 'yes', 'on', '1', 1)
        cmp_type = request.data.get('cmp_type') if is_cmp_patient else None

        if not name or not phone_number or not password or not age or not gender:
            return Response({'error': 'Name, phone number, password, age, and gender are required.'}, status=status.HTTP_400_BAD_REQUEST)

        if login_type == 'corporate' and not company_name:
             return Response({'error': 'Company name is required for corporate login.'}, status=status.HTTP_400_BAD_REQUEST)

        valid_cmp_types = {choice[0] for choice in Patient.CMP_TYPE_CHOICES}
        if is_cmp_patient and cmp_type not in valid_cmp_types:
            return Response({'error': 'Please select a valid CMP type.'}, status=status.HTTP_400_BAD_REQUEST)

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
            designation=designation if login_type == 'corporate' else None,
            is_cmp_patient=is_cmp_patient,
            cmp_type=cmp_type
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
            
            # Record monthly login
            from optometrist.models import UserLoginStat
            now = timezone.now()
            year_month = now.strftime('%Y-%m')
            stat, _ = UserLoginStat.objects.get_or_create(user=user, year_month=year_month)
            stat.login_count += 1
            stat.save(update_fields=['login_count'])
            
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

        # ===== CMP (Chronic Management Program) data — view only =====
        cmp_patient = patient_records.filter(is_cmp_patient=True).order_by('-created_at').first()
        cmp_records = CMPRecord.objects.filter(
            patient__in=patient_records
        ).select_related('optometrist').order_by('-recorded_at')
        context['cmp_patient'] = cmp_patient
        context['is_cmp_patient'] = cmp_patient is not None
        context['cmp_type'] = cmp_patient.cmp_type if cmp_patient else None
        context['cmp_type_display'] = cmp_patient.get_cmp_type_display() if cmp_patient and cmp_patient.cmp_type else None
        context['cmp_is_diabetic'] = cmp_patient.is_diabetic_cmp if cmp_patient else False
        context['cmp_is_pediatric'] = cmp_patient.is_pediatric_myopia_cmp if cmp_patient else False
        context['cmp_records'] = cmp_records
        context['cmp_latest'] = cmp_records.first()

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

        # Include CMP clinical data so the report carries the full picture for CMP patients
        patient = exam.patient
        if patient.phone_number:
            patient_records = Patient.objects.filter(phone_number=patient.phone_number)
        else:
            patient_records = Patient.objects.filter(pk=patient.pk)
        cmp_records = CMPRecord.objects.filter(
            patient__in=patient_records
        ).select_related('optometrist').order_by('-recorded_at')
        cmp_patient = patient_records.filter(is_cmp_patient=True).order_by('-created_at').first()

        context = {
            'exam': exam,
            'cmp_patient': cmp_patient,
            'is_cmp_patient': cmp_patient is not None,
            'cmp_records': cmp_records,
            'cmp_latest': cmp_records.first(),
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
            formatted_time = "0h 0m 0s"
            if elapsed > 0:
                user = request.user
                # Use F() expression for safe concurrent updates
                from django.db.models import F
                Optometrist.objects.filter(pk=user.pk).update(
                    retention_time=F('retention_time') + elapsed
                )
                
                # Update DailyUserUsage
                from optometrist.models import DailyUserUsage, DailyTopTen
                from django.utils import timezone
                today = timezone.localdate()
                usage, created = DailyUserUsage.objects.get_or_create(user=user, date=today)
                usage.total_seconds = F('total_seconds') + elapsed
                usage.save(update_fields=['total_seconds'])
                
                # Update DailyTopTen
                top_users = DailyUserUsage.objects.filter(date=today).order_by('-total_seconds')[:10]
                top_users_data = []
                for tu in top_users:
                    # tu.total_seconds might be an F expression if not refreshed, so let's get the actual value.
                    # It's better to fetch fresh from DB since we are building top 10.
                    pass
                
                # We need fresh values, so let's evaluate the queryset
                top_users_list = list(top_users.select_related('user'))
                for tu in top_users_list:
                    top_users_data.append({
                        'user_id': tu.user.id,
                        'name': tu.user.name,
                        'phone_number': tu.user.phone_number,
                        'total_seconds': tu.total_seconds
                    })
                
                daily_top, _ = DailyTopTen.objects.get_or_create(date=today)
                daily_top.top_users_data = top_users_data
                daily_top.save(update_fields=['top_users_data'])

                user.refresh_from_db()
                total_seconds = user.retention_time
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                formatted_time = f"{hours}h {minutes}m {seconds}s"
            return Response({'status': 'ok', 'formatted_time': formatted_time})
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

from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail

class RequestOTPView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        phone_number = request.data.get('phone_number')
        if not phone_number:
            return Response({'error': 'Phone number is required'}, status=400)
        user = Optometrist.objects.filter(phone_number=phone_number).first()
        if not user:
            return Response({'error': 'User not found'}, status=404)
            
        if not user.email:
            return Response({'error': 'No email address registered for this account. Please contact support.'}, status=400)
        
        token = default_token_generator.make_token(user)
        
        try:
            send_mail(
                'Password Reset Token - EyeSphere',
                f'Hello {user.name},\n\nYour password reset token is: {token}\n\nPlease copy and paste this token into the portal to securely reset your password.',
                'noreply@eyesphere.com',
                [user.email],
                fail_silently=False,
            )
            # Print token to console for testing locally
            print(f"\n========== Sent Email to {user.email} with token: {token} ==========\n")
            
            # Mask the email for privacy in the response
            email_parts = user.email.split('@')
            masked_email = f"{email_parts[0][:2]}***@{email_parts[1]}"
            return Response({'message': f'Reset token sent to {masked_email}.'})
        except Exception as e:
            print(f"Email failed: {e}")
            # Fallback for development if email server isn't configured
            print(f"\n========== Email Failed. Token for {phone_number} is {token} ==========\n")
            return Response({'message': 'Reset token generated (Check console since email failed).'})

class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        phone_number = request.data.get('phone_number')
        token = request.data.get('otp')
        new_password = request.data.get('new_password')
        
        if not all([phone_number, token, new_password]):
            return Response({'error': 'All fields are required'}, status=400)
            
        user = Optometrist.objects.filter(phone_number=phone_number).first()
        if not user:
            return Response({'error': 'User not found'}, status=404)
            
        if not default_token_generator.check_token(user, token):
            return Response({'error': 'Invalid or expired reset token'}, status=400)
            
        user.set_password(new_password)
        user.save()
        
        return Response({'message': 'Password reset successfully. You can now login.'})

class ChangePasswordView(APIView):
    authentication_classes = [CsrfExemptSessionAuth]
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')
        
        if not all([new_password, confirm_password]):
            return Response({'error': 'New password and confirm password are required'}, status=400)
            
        if new_password != confirm_password:
            return Response({'error': 'Passwords do not match'}, status=400)
            
        user = request.user
            
        user.set_password(new_password)
        user.save()
        
        # Keep user logged in after password change
        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(request, user)
        
        return Response({'message': 'Password changed successfully.'})

class GetOptometristsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        optometrists = Optometrist.objects.filter(role='optometrist').values('id', 'name', 'phone_number')
        return Response({'status': 'success', 'optometrists': list(optometrists)})

class BookHomeTestView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        try:
            data = request.data
            optometrist_id = data.get('optometrist_id')
            phone_number = data.get('phone_number')
            email = data.get('email')
            company_name = data.get('company_name')
            address = data.get('address')
            
            optometrist = get_object_or_404(Optometrist, id=optometrist_id, role='optometrist')
            
            HomeTestRequest.objects.create(
                user=request.user,
                optometrist=optometrist,
                phone_number=phone_number,
                email=email,
                company_name=company_name,
                address=address
            )
            return Response({'status': 'success', 'message': 'Home test booked successfully'})
        except Exception as e:
            return Response({'error': str(e)}, status=400)

class GetPatientProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        user = request.user
        patient_record = Patient.objects.filter(phone_number=user.phone_number).first()
        return Response({
            'name': user.name,
            'phone_number': user.phone_number,
            'email': user.email,
            'coins': user.coins,
            'age': patient_record.age if patient_record else None,
            'gender': patient_record.gender if patient_record else None,
            'address': patient_record.address if patient_record else None,
            'login_type': patient_record.login_type if patient_record else 'at_home',
            'company_name': patient_record.company_name if patient_record else None,
            'designation': patient_record.designation if patient_record else None,
        })

class SubmitPatientQueryView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        try:
            data = request.data
            query_text = data.get('query_text')
            if not query_text:
                return Response({'error': 'Query text is required'}, status=400)
            
            PatientQuery.objects.create(
                user=request.user,
                name=request.user.name,
                phone_number=request.user.phone_number,
                email=request.user.email,
                query_text=query_text
            )
            return Response({'status': 'success', 'message': 'Query submitted successfully'})
        except Exception as e:
            return Response({'error': str(e)}, status=400)

from django.db.models import Avg

class PlatformTimeMetricsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from optometrist.models import DailyUserUsage, DailyTopTen
        from django.utils import timezone
        import datetime
        
        date_str = request.query_params.get('date')
        month_str = request.query_params.get('month')
        
        today = timezone.localdate()
        
        target_date = today
        if date_str:
            try:
                target_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
                
        target_month_year = today.strftime('%Y-%m')
        if month_str:
            target_month_year = month_str
        
        # Calculate daily average
        daily_usages = DailyUserUsage.objects.filter(date=target_date)
        daily_avg_dict = daily_usages.aggregate(average_time=Avg('total_seconds'))
        daily_average = daily_avg_dict['average_time'] or 0.0
        
        # Calculate monthly average
        # Format for year-month filter: year and month
        try:
            year, month = map(int, target_month_year.split('-'))
            monthly_usages = DailyUserUsage.objects.filter(date__year=year, date__month=month)
            monthly_avg_dict = monthly_usages.aggregate(average_time=Avg('total_seconds'))
            monthly_average = monthly_avg_dict['average_time'] or 0.0
        except ValueError:
            monthly_average = 0.0
            
        # Get daily top 10
        daily_top_10 = []
        try:
            top_ten_record = DailyTopTen.objects.get(date=target_date)
            daily_top_10 = top_ten_record.top_users_data
        except DailyTopTen.DoesNotExist:
            pass
            
        return Response({
            'status': 'success',
            'date': target_date.strftime('%Y-%m-%d'),
            'month': target_month_year,
            'daily_average_seconds': round(daily_average, 2),
            'monthly_average_seconds': round(monthly_average, 2),
            'daily_top_10': daily_top_10
        })
