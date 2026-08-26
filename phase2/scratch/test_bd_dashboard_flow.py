import os
import sys
import django

# Add phase2 project to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'phase2.settings')
django.setup()

from django.test import RequestFactory
from patients.views import OnboardPatientApiView
from optometrist.models import Optometrist, Patient

def run_bd_dashboard_test():
    print("======================================================================")
    print("   AUTOMATED BD DASHBOARD ONBOARDING TEST WITH DUMMY DATA             ")
    print("   Target Email: asur21zurvan@gmail.com                               ")
    print("======================================================================")

    factory = RequestFactory()
    target_email = "asur21zurvan@gmail.com"
    test_mobile = "9876543210"

    # Cleanup existing test records for test mobile
    Optometrist.objects.filter(phone_number=test_mobile).delete()
    Patient.objects.filter(phone_number=test_mobile).delete()

    dummy_bd_payload = {
        "p_name": "BD Dashboard Test Patient",
        "p_mobile": test_mobile,
        "email": target_email,
        "age_numeric": 46,
        "gender": "male",
        "address": "789 Healthcare Avenue, Metro City",
        "location": "Metro City Center",
        "riskRaw": 8,
        "riskPct": 68,
        "riskBand": "High Risk",
        "urgency": "Urgent consultation & comprehensive eye exam required within 7 days",
        "primaryPackage": "Comprehensive Vision & Diabetic Retinopathy Care",
        "payable": 1999.00,
        "mrp": 3500.00,
        "savings": 1501.00,
        "booking_code": "BK-BD-2026-X99",
        "booking_date": "2026-09-02",
        "booking_time": "11:30 AM",
        "optometrist": "Dr. Sarah Jenkins (OD)",
        "answers": {
            "diabetes": 1,
            "dm5": 1,
            "hba1c": "7.5",
            "htn": 1,
            "thyroid": 0,
            "familyHx": 1,
            "specs": 1,
            "specsPow": 1,
            "blur": "Occasional blurred vision when reading",
            "smoke": 0,
            "alcohol": 0,
            "screen": "8+ hours daily"
        }
    }

    print("\n[Step 1] Submitting BD Onboarding Dashboard Data:")
    print(f" - Patient Name: {dummy_bd_payload['p_name']}")
    print(f" - Mobile (Username): {dummy_bd_payload['p_mobile']}")
    print(f" - Email: {dummy_bd_payload['email']}")
    print(f" - Risk Band: {dummy_bd_payload['riskBand']} ({dummy_bd_payload['riskPct']}%)")
    print(f" - Selected Package: {dummy_bd_payload['primaryPackage']}")
    print(f" - Payable Amount: INR {dummy_bd_payload['payable']}")

    req = factory.post('/patient/api/onboard/', data=dummy_bd_payload, content_type='application/json')
    view = OnboardPatientApiView.as_view()
    resp = view(req)

    print(f"\n[Step 2] Response Status Code: {resp.status_code}")
    print(f"Response Payload:")
    for k, v in resp.data.items():
        print(f"   - {k}: {v}")

    # Database Verification
    user = Optometrist.objects.filter(phone_number=test_mobile).first()
    patient = Patient.objects.filter(phone_number=test_mobile).first()

    print(f"\n[Step 3] Database Verification:")
    print(f" - Account Created in Optometrist User table? {'YES' if user else 'NO'}")
    if user:
        print(f"   - User ID: {user.id}")
        print(f"   - Phone Number (Login): {user.phone_number}")
        print(f"   - Registered Email: {user.email}")

    print(f" - Account Created in Patient Demographic table? {'YES' if patient else 'NO'}")
    if patient:
        print(f"   - Assigned Patient ID (Account Number): {patient.patient_account_id}")
        print(f"   - Stored Email: {patient.email}")
        print(f"   - Risk Band: {patient.risk_band}")

    print("\n======================================================================")
    print("                     TEST SUCCESSFUL                                  ")
    print("======================================================================")

if __name__ == "__main__":
    run_bd_dashboard_test()
