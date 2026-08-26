import os
import sys
import django

# Add phase2 project to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'phase2.settings')
django.setup()

from django.test import RequestFactory
from patients.views import RegisterPatient, OnboardPatientApiView
from optometrist.models import Optometrist, Patient

def run_dummy_test():
    print("======================================================================")
    print("      Testing Account Creation & Credential Email Module              ")
    print("      Target Email: asur21zurvan@gmail.com                            ")
    print("======================================================================")

    factory = RequestFactory()
    target_email = "asur21zurvan@gmail.com"

    # --- TEST 1: BD / Patient Registration API ---
    phone_1 = "9911223344"
    print(f"\n[Step 1] Cleaning up any existing records for test mobile: {phone_1}...")
    Optometrist.objects.filter(phone_number=phone_1).delete()
    Patient.objects.filter(phone_number=phone_1).delete()

    reg_payload = {
        "name": "Dummy Account - Patient Reg",
        "phone_number": phone_1,
        "email": target_email,
        "password": "SecureDummyPass123!",
        "age": 34,
        "gender": "male",
        "login_type": "corporate",
        "company_name": "EyeSphere Tech Corp",
        "designation": "Software Specialist",
        "address": "123 Innovation Way, Tech Park"
    }

    print(f"\n[Step 2] Sending POST to /patient/api/register/ with dummy data:")
    print(f" - Name: {reg_payload['name']}")
    print(f" - Mobile (Username): {reg_payload['phone_number']}")
    print(f" - Email: {reg_payload['email']}")
    print(f" - Company: {reg_payload['company_name']}")

    req1 = factory.post('/patient/api/register/', data=reg_payload, content_type='application/json')
    view1 = RegisterPatient.as_view()
    resp1 = view1(req1)

    print(f"\n[Step 3] RegisterPatient Response Status: {resp1.status_code}")
    print(f"Response Payload: {resp1.data}")

    # Verify Patient in Database
    created_user = Optometrist.objects.filter(phone_number=phone_1).first()
    created_patient = Patient.objects.filter(phone_number=phone_1).first()
    print(f"\n[Database Verification]:")
    print(f" - Optometrist User ID: {created_user.id if created_user else 'NOT FOUND'}")
    print(f" - Assigned Patient ID (Account Number): {created_patient.patient_account_id if created_patient else 'NOT FOUND'}")

    # --- TEST 2: Patient Onboarding API ---
    phone_2 = "9955443322"
    print(f"\n----------------------------------------------------------------------")
    print(f"[Step 4] Cleaning up any existing records for onboarding mobile: {phone_2}...")
    Optometrist.objects.filter(phone_number=phone_2).delete()
    Patient.objects.filter(phone_number=phone_2).delete()

    onboard_payload = {
        "p_name": "Dummy Account - Onboarding",
        "p_mobile": phone_2,
        "email": target_email,
        "age": 42,
        "gender": "female",
        "riskPct": 52,
        "riskBand": "Moderate Risk",
        "urgency": "Detailed evaluation recommended within 14 days",
        "primaryPackage": "Comprehensive Vision & Dry Eye Wellness Package",
        "payable": 1850.00,
        "booking_code": "BK-EYESPHERE-2026",
        "booking_date": "2026-09-05",
        "booking_time": "11:00 AM"
    }

    print(f"\n[Step 5] Sending POST to /patient/api/onboard/ with dummy data:")
    print(f" - Name: {onboard_payload['p_name']}")
    print(f" - Mobile (Username): {onboard_payload['p_mobile']}")
    print(f" - Email: {onboard_payload['email']}")
    print(f" - Vision Risk Score: {onboard_payload['riskPct']}% ({onboard_payload['riskBand']})")
    print(f" - Selected Package: {onboard_payload['primaryPackage']}")

    req2 = factory.post('/patient/api/onboard/', data=onboard_payload, content_type='application/json')
    view2 = OnboardPatientApiView.as_view()
    resp2 = view2(req2)

    print(f"\n[Step 6] OnboardPatientApiView Response Status: {resp2.status_code}")
    print(f"Response Payload: {resp2.data}")

    onboard_user = Optometrist.objects.filter(phone_number=phone_2).first()
    onboard_patient = Patient.objects.filter(phone_number=phone_2).first()
    print(f"\n[Database Verification]:")
    print(f" - Optometrist User ID: {onboard_user.id if onboard_user else 'NOT FOUND'}")
    print(f" - Assigned Patient ID: {onboard_patient.patient_account_id if onboard_patient else 'NOT FOUND'}")
    print(f" - Auto-Generated Password: {resp2.data.get('password')}")

    print("\n======================================================================")
    print("       TEST COMPLETE - ALL DUMMY ACCOUNT DATA CREATED                ")
    print("======================================================================")

if __name__ == "__main__":
    run_dummy_test()
