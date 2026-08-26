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
from .models import ScreeningTestResult, OnlineSessionRequest, RedeemableService, RedemptionTicket, HomeTestRequest, PatientQuery
import json
import random
import secrets
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
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

        # Check if email is already registered to another account
        if email and Optometrist.objects.filter(email=email).exists():
            return Response({'error': 'This email address is already registered to another account.'}, status=status.HTTP_400_BAD_REQUEST)

        patient_account_id = f"ES-{random.randint(100000, 999999)}"

        # Create patient user account for login
        user = Optometrist.objects.create_user(
            phone_number=phone_number,
            name=name,
            password=password,
            email=email if email else None,
            role='patient'
        )
        
        # Create actual Patient record in the database
        patient = Patient.objects.create(
            name=name,
            phone_number=phone_number,
            age=age,
            gender=gender,
            address=address,
            login_type=login_type,
            company_name=company_name if login_type == 'corporate' else None,
            designation=designation if login_type == 'corporate' else None,
            email=email if email else None,
            patient_account_id=patient_account_id
        )

        email_sent, email_status_msg = False, ""
        if email:
            email_sent, email_status_msg = send_patient_credentials_email(
                name=name,
                patient_account_id=patient_account_id,
                mobile=phone_number,
                password=password,
                email=email
            )
        else:
            email_status_msg = "No email address provided; account created with phone number login."

        return Response({
            'message': 'Account created successfully!',
            'status': 'success',
            'patient_id': patient_account_id,
            'user': {
                'id': user.id,
                'name': user.name,
                'phone_number': user.phone_number,
                'email': user.email,
                'patient_account_id': patient_account_id,
            },
            'email_sent': email_sent,
            'email_status': email_status_msg
        }, status=status.HTTP_201_CREATED)


class LoginPatient(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return render(request, 'patients/login.html')

    def post(self, request):
        phone_number = request.data.get('phone_number')
        patient_id = request.data.get('patient_id') or request.data.get('username')
        password = request.data.get('password')

        # Patient IDs are printed on the onboarding confirmation and are also
        # accepted as usernames; phone-number login remains backwards compatible.
        supplied_username = patient_id or phone_number
        if supplied_username and str(supplied_username).upper().startswith('ES-'):
            patient = Patient.objects.filter(patient_account_id=supplied_username).first()
            phone_number = patient.phone_number if patient else None

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
            formatted_time = "0h 0m 0s"
            if elapsed > 0:
                user = request.user
                # Use F() expression for safe concurrent updates
                from django.db.models import F
                Optometrist.objects.filter(pk=user.pk).update(
                    retention_time=F('retention_time') + elapsed
                )
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


def send_patient_credentials_email(
    name,
    patient_account_id,
    mobile,
    password,
    email,
    risk_score_pct=None,
    risk_band=None,
    urgency=None,
    primary_package=None,
    payable_amount=None,
    booking_code=None,
    booking_date=None,
    booking_time=None
):
    """
    Sends automated patient credentials (Account Number/Patient ID & Password) via Django mail (EmailMultiAlternatives).
    Returns (email_sent: bool, email_status_msg: str)
    """
    if not email:
        return False, "No email address provided; account created with phone number login."

    subject = f"Welcome to EyeSphere - Your Patient Credentials & Vision Report [{patient_account_id}]"

    summary_text = ""
    summary_html = ""

    if risk_score_pct is not None:
        summary_text = f"""
--- YOUR VISION ASSESSMENT SUMMARY ---
Risk Assessment Score: {risk_score_pct}% ({risk_band or 'N/A'})
Follow-up / Urgency: {urgency if urgency else 'Routine screening'}
Primary Package / Screenings: {primary_package if primary_package else 'Custom Selection'}
Total Payable: INR {payable_amount if payable_amount is not None else 0.00}
{'Booking Reference: ' + str(booking_code) if booking_code else ''}
{'Scheduled Visit Date: ' + str(booking_date) + ' (' + str(booking_time) + ')' if booking_date else ''}
"""
        risk_color = '#d9534f' if risk_score_pct >= 60 else '#f0ad4e' if risk_score_pct >= 35 else '#5cb85c'
        payable_str = f"{payable_amount:.2f}" if isinstance(payable_amount, (int, float)) else str(payable_amount or '0.00')
        booking_ref_html = f'<p style="margin: 6px 0; font-size: 14px;"><strong>Booking Ref:</strong> {booking_code} ({booking_date} {booking_time})</p>' if booking_code else ''

        summary_html = f"""
        <div style="background-color: #fafbfc; border: 1px solid #eee; padding: 15px 20px; margin: 20px 0; border-radius: 6px;">
            <h3 style="margin-top: 0; color: #0a2b3b; font-size: 16px;">📊 Vision Assessment Summary</h3>
            <p style="margin: 6px 0; font-size: 14px;"><strong>Risk Index Score:</strong> <span style="color: {risk_color}; font-weight: bold;">{risk_score_pct}% ({risk_band or 'N/A'})</span></p>
            <p style="margin: 6px 0; font-size: 14px;"><strong>Follow-up Recommendation:</strong> {urgency if urgency else 'Routine check'}</p>
            <p style="margin: 6px 0; font-size: 14px;"><strong>Selected Package:</strong> {primary_package if primary_package else 'Custom Screenings'}</p>
            <p style="margin: 6px 0; font-size: 14px;"><strong>Total Amount:</strong> ₹{payable_str}</p>
            {booking_ref_html}
        </div>
        """

    plain_body = f"""Dear {name},

Welcome to EyeSphere Vision Wellness! Your patient account has been successfully created.

--- ACCOUNT CREDENTIALS ---
Patient ID: {patient_account_id}
Login Username (Mobile): {mobile}
Login Password: {password}
Login Portal: https://netrascreen.in/patient/api/login/
{summary_text}
Please log in to your patient portal to track your vision screening reports, manage home test bookings, and consult with our eye specialists.

Warm regards,
EyeSphere Vision Wellness Team
https://netrascreen.in
"""

    html_body = f"""
    <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #e0e0e0; border-radius: 10px; overflow: hidden; background-color: #ffffff;">
        <div style="background-color: #0a2b3b; color: #ffffff; padding: 25px; text-align: center;">
            <h1 style="margin: 0; font-size: 24px; color: #c9a55c; letter-spacing: 2px;">EYESPHERE</h1>
            <p style="margin: 5px 0 0 0; font-size: 12px; color: #f0dba8; letter-spacing: 1px;">VISION BEYOND LIMITS</p>
        </div>
        
        <div style="padding: 30px; color: #333333;">
            <h2 style="color: #0a2b3b; margin-top: 0;">Welcome, {name}!</h2>
            <p style="font-size: 15px; line-height: 1.5;">Your EyeSphere patient account and login credentials have been successfully created.</p>
            
            <div style="background-color: #f7f9fa; border-left: 4px solid #c9a55c; padding: 15px 20px; margin: 20px 0; border-radius: 4px;">
                <h3 style="margin-top: 0; color: #0a2b3b; font-size: 16px;">🔑 Your Login Credentials</h3>
                <p style="margin: 6px 0; font-size: 14px;"><strong>Patient ID:</strong> <span style="color: #0a2b3b; font-weight: bold;">{patient_account_id}</span></p>
                <p style="margin: 6px 0; font-size: 14px;"><strong>Mobile (Login Username):</strong> {mobile}</p>
                <p style="margin: 6px 0; font-size: 14px;"><strong>Password:</strong> <span style="background: #eef2f5; padding: 2px 8px; border-radius: 4px; font-family: monospace; font-weight: bold;">{password}</span></p>
                <p style="margin: 12px 0 0 0;"><a href="https://netrascreen.in/patient/api/login/" style="display: inline-block; background-color: #0a2b3b; color: #ffffff; text-decoration: none; padding: 8px 16px; border-radius: 5px; font-weight: bold; font-size: 13px;">Log In to Patient Portal →</a></p>
            </div>
            
            {summary_html}

            <p style="font-size: 13px; color: #777;">If you have any questions or need to modify your booking, please contact our support team at support@eyesphere.com.</p>
        </div>

        <div style="background-color: #f1f5f8; padding: 15px; text-align: center; font-size: 12px; color: #666; border-top: 1px solid #e0e0e0;">
            EyeSphere Vision Wellness &copy; 2026. All rights reserved.
        </div>
    </div>
    """

    host_user = getattr(settings, 'EMAIL_HOST_USER', '')
    is_placeholder = not host_user or 'your_email' in host_user or 'example' in host_user
    if getattr(settings, 'EMAIL_BACKEND', '') == 'django.core.mail.backends.smtp.EmailBackend' and is_placeholder:
        print(f"[MAIL LOG] Automated Credential Email generated for {name} ({email}):\nSubject: {subject}\nPatient ID: {patient_account_id}\nUsername: {mobile}\nPassword: {password}\n(Placeholder SMTP credentials detected in .env; email logged locally)")
        return True, f"Credentials generated for {email}. (Logged locally to console; update EMAIL_HOST_USER/PASSWORD in .env to send via live SMTP)"

    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_body,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@eyesphere.com'),
            to=[email]
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)
        return True, f"Credentials emailed successfully to {email}."
    except Exception as mail_err:
        print(f"Email delivery error: {mail_err}")
        return False, f"Account created, but email could not be sent: {str(mail_err)}"

class PatientOnboardingView(TemplateView):
    template_name = 'patients/onboarding.html'


class OnboardPatientApiView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        try:
            data = request.data if isinstance(request.data, dict) else json.loads(request.body)
            
            # Extract basic patient details
            name = (data.get('name') or data.get('p_name') or '').strip()
            mobile = (data.get('mobile') or data.get('phone_number') or data.get('p_mobile') or '').strip()
            email = (data.get('email') or '').strip()
            location = data.get('location') or data.get('p_loc') or ''
            location_other = data.get('location_other') or data.get('p_loc_other') or ''
            age_group = data.get('age_group') or data.get('age') or '' # under40, 40to49, 50plus
            
            # Numeric age derivation
            raw_age = data.get('age_numeric') or data.get('age_years')
            if not raw_age:
                if age_group == 'under40': raw_age = 30
                elif age_group == '40to49': raw_age = 45
                elif age_group == '50plus': raw_age = 58
                else: raw_age = 35
            try:
                age = int(raw_age)
            except (ValueError, TypeError):
                age = 35

            gender = data.get('gender') or 'other'
            address = data.get('address') or location or ''

            if not name or not mobile:
                return Response({'error': 'Patient Name and Mobile Number are required.'}, status=status.HTTP_400_BAD_REQUEST)

            # Systemic medical history
            answers = data.get('answers') or {}
            diabetes = bool(int(answers.get('diabetes', 0) or data.get('diabetes', 0) or 0))
            diabetes_over_5yrs = bool(int(answers.get('dm5', 0) or data.get('dm5', 0) or 0))
            hba1c_level = answers.get('hba1c') or data.get('hba1c') or ''
            hypertension = bool(int(answers.get('htn', 0) or data.get('htn', 0) or 0))
            thyroid = bool(int(answers.get('thyroid', 0) or data.get('thyroid', 0) or 0))
            family_history = bool(int(answers.get('familyHx', 0) or answers.get('fh', 0) or data.get('fh', 0) or 0))
            steroid_use = bool(int(answers.get('steroid', 0) or data.get('steroid', 0) or 0))

            # Eye & Vision health history
            spectacles_use = bool(int(answers.get('specs', 0) or data.get('specs', 0) or 0))
            spectacles_power_high = bool(int(answers.get('specsPow', 0) or data.get('specspow', 0) or 0))
            last_checkup = answers.get('checkupOld') or data.get('checkup') or ''
            blurred_vision = answers.get('blur') or data.get('blur') or ''
            symptoms = answers.get('symptoms') or data.get('symptoms') or ''

            # Lifestyle factors
            smoking = bool(int(answers.get('smoking', 0) or answers.get('smoke', 0) or data.get('smoke', 0) or 0))
            alcohol = bool(int(answers.get('alcohol', 0) or data.get('alcohol', 0) or 0))
            screen_time = answers.get('screen') or data.get('screen') or ''
            physical_activity = answers.get('activity') or data.get('activity') or ''

            # Risk scoring & output
            risk_score_raw = int(data.get('riskRaw') or data.get('risk_score_raw') or 0)
            risk_score_pct = int(data.get('riskPct') or data.get('risk_score_pct') or 0)
            risk_band = data.get('riskBand') or data.get('risk_band') or 'Low risk'
            urgency = data.get('urgency') or ''
            conversion_likelihood = data.get('convLikelihood') or data.get('conv_likelihood') or ''
            disease_top3 = data.get('diseaseTop3') or data.get('disease_top3') or []
            selected_tests = data.get('tests') or data.get('selected_tests') or ''

            # Package Deal & Booking Details
            primary_package = data.get('primaryPackage') or data.get('primary_package') or ''
            free_basic = data.get('freeBasic') == 'Yes' or data.get('free_basic') is True
            add_on_people = data.get('addOns') or data.get('add_on_people') or []
            people_count = int(data.get('peopleCount') or data.get('people_count') or 1)
            payable_amount = float(data.get('payable') or data.get('payable_amount') or 0.0)
            mrp_amount = float(data.get('mrp') or data.get('mrp_amount') or 0.0)
            savings_amount = float(data.get('savings') or data.get('savings_amount') or 0.0)
            tele_charge = float(data.get('teleCharge') or data.get('tele_charge') or 0.0)
            ta_charge = float(data.get('taCharge') or data.get('ta_charge') or 0.0)
            manual_discount = float(data.get('mdisc') or data.get('manual_discount') or 0.0)
            referral_code = data.get('referral') or data.get('referral_code') or ''
            booking_code = data.get('booking_code') or data.get('code') or ''
            booking_date = data.get('booking_date') or data.get('date') or ''
            booking_time = data.get('booking_time') or data.get('time') or ''
            optometrist_assigned = data.get('optometrist') or data.get('optometrist_assigned') or ''
            special_notes = data.get('msg') or data.get('special_notes') or ''

            # Categorize risk_factor for Patient model
            if risk_score_pct >= 65 or 'High' in risk_band or 'Urgent' in urgency:
                risk_factor = 'high'
            elif risk_score_pct >= 35 or 'Moderate' in risk_band:
                risk_factor = 'moderate'
            else:
                risk_factor = 'low'

            # Step 1: Create/Get Patient User Account (Optometrist model with role='patient')
            user = Optometrist.objects.filter(phone_number=mobile).first()
            is_new_user = False
            
            if not user:
                # Make the credential recognizable to the patient while retaining
                # enough random entropy that it cannot be guessed from the profile.
                name_fragment = ''.join(
                    character for character in name.upper()
                    if character.isascii() and character.isalnum()
                )[:5] or 'PATIENT'
                phone_suffix = ''.join(character for character in mobile if character.isdigit())[-4:]
                random_suffix = ''.join(
                    secrets.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789')
                    for _ in range(8)
                )
                generated_password = f"ES@{name_fragment}{phone_suffix}{age}{random_suffix}"
                
                # Assign email only if not taken by another user account
                user_email = email if email and not Optometrist.objects.filter(email=email).exists() else None

                user = Optometrist.objects.create_user(
                    phone_number=mobile,
                    name=name,
                    password=generated_password,
                    email=user_email,
                    role='patient'
                )
                is_new_user = True
            else:
                # User already exists
                if email and not user.email and not Optometrist.objects.filter(email=email).exclude(pk=user.pk).exists():
                    user.email = email
                    user.save(update_fields=['email'])
                generated_password = "[Existing Password Maintained]"

            # Generate Patient Account ID
            ts_hash = abs(hash(mobile + str(timezone.now().timestamp()))) % 1000000
            patient_account_id = data.get('pid') or f"ES-{str(ts_hash).zfill(6)}"

            # Step 2: Create/Update Patient Record
            patient_record, created = Patient.objects.update_or_create(
                phone_number=mobile,
                defaults={
                    'name': name,
                    'age': age,
                    'gender': gender,
                    'address': address,
                    'email': email if email else None,
                    'location': location,
                    'location_other': location_other,
                    'age_group': age_group,
                    'diabetes': diabetes,
                    'diabetes_over_5yrs': diabetes_over_5yrs,
                    'hba1c_level': hba1c_level,
                    'hypertension': hypertension,
                    'thyroid': thyroid,
                    'family_history': family_history,
                    'steroid_use': steroid_use,
                    'spectacles_use': spectacles_use,
                    'spectacles_power_high': spectacles_power_high,
                    'last_checkup': last_checkup,
                    'blurred_vision': blurred_vision,
                    'symptoms': str(symptoms),
                    'smoking': smoking,
                    'alcohol': alcohol,
                    'screen_time': screen_time,
                    'physical_activity': physical_activity,
                    'risk_score_raw': risk_score_raw,
                    'risk_score_pct': risk_score_pct,
                    'risk_band': risk_band,
                    'urgency': urgency,
                    'conversion_likelihood': conversion_likelihood,
                    'disease_top3': disease_top3 if isinstance(disease_top3, list) else [],
                    'selected_tests': str(selected_tests),
                    'primary_package': primary_package,
                    'free_basic': free_basic,
                    'add_on_people': add_on_people if isinstance(add_on_people, list) else [],
                    'people_count': people_count,
                    'payable_amount': payable_amount,
                    'mrp_amount': mrp_amount,
                    'savings_amount': savings_amount,
                    'tele_charge': tele_charge,
                    'ta_charge': ta_charge,
                    'manual_discount': manual_discount,
                    'referral_code': referral_code,
                    'booking_code': booking_code,
                    'booking_date': booking_date,
                    'booking_time': booking_time,
                    'optometrist_assigned': optometrist_assigned,
                    'special_notes': special_notes,
                    'patient_account_id': patient_account_id,
                    'raw_answers': answers if isinstance(answers, dict) else {},
                    'risk_factor': risk_factor
                }
            )

            # Step 3: Send Email with credentials to Patient
            target_email = email or user.email

            email_sent, email_status_msg = send_patient_credentials_email(
                name=name,
                patient_account_id=patient_account_id,
                mobile=mobile,
                password=generated_password,
                email=target_email,
                risk_score_pct=risk_score_pct,
                risk_band=risk_band,
                urgency=urgency,
                primary_package=primary_package,
                payable_amount=payable_amount,
                booking_code=booking_code,
                booking_date=booking_date,
                booking_time=booking_time
            )

            return Response({
                'status': 'success',
                'message': 'Patient successfully onboarded and backend record created!',
                'patient_id': patient_account_id,
                'patient_name': name,
                'phone_number': mobile,
                'email': target_email,
                'password': generated_password,
                'is_new_user': is_new_user,
                'email_sent': email_sent,
                'email_status': email_status_msg
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': f'Failed to onboard patient: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

