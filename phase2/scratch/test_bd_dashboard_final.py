import os
import sys
import random
import string
import django

# Add phase2 project to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'phase2.settings')
django.setup()

from django.test import RequestFactory
from patients.views import OnboardPatientApiView
from optometrist.models import Optometrist, Patient

def test_bd_dashboard_entry():
    print("======================================================================")
    print("      BD DASHBOARD AUTOMATED ONBOARDING & CREDENTIAL EMAIL TEST        ")
    print("      Target Email: asur21zurvan@gmail.com                            ")
    print("======================================================================")

    factory = RequestFactory()
    target_email = "asur21zurvan@gmail.com"
    
    # Generate unique mobile number to test fresh account creation
    dummy_mobile = f"98765{random.randint(10005, 99999)}"
    patient_name = "Zurvan BD Test Patient"

    # Cleanup any prior test record with this dummy mobile
    Optometrist.objects.filter(phone_number=dummy_mobile).delete()
    Patient.objects.filter(phone_number=dummy_mobile).delete()

    print(f"\n[Step 1] Preparing Dummy Patient Entry on BD Dashboard:")
    print(f" - Patient Name: {patient_name}")
    print(f" - Mobile (Login Username): {dummy_mobile}")
    print(f" - Email Address: {target_email}")
    print(f" - Age / Gender: 38 / Male")
    print(f" - Location: West Delhi - Dwarka Sector 12")

    bd_onboarding_payload = {
        "p_name": patient_name,
        "p_mobile": dummy_mobile,
        "email": target_email,
        "age_numeric": 38,
        "gender": "male",
        "address": "Flat 402, Royal Palms, Sector 12, Dwarka, New Delhi",
        "location": "Dwarka Sector 12",
        "riskRaw": 7,
        "riskPct": 62,
        "riskBand": "Moderate to High Risk",
        "urgency": "Follow-up screening & optometrist consultation recommended within 10 days",
        "primaryPackage": "Comprehensive Vision & Diabetic Retinopathy Care",
        "payable": 1699.00,
        "mrp": 2800.00,
        "savings": 1101.00,
        "booking_code": f"BK-BD-{random.randint(1000, 9999)}",
        "booking_date": "2026-09-04",
        "booking_time": "10:30 AM",
        "optometrist": "Dr. Rajesh Kumar (Senior Optometrist)",
        "answers": {
            "diabetes": 1,
            "dm5": 0,
            "hba1c": "6.8",
            "htn": 1,
            "thyroid": 0,
            "familyHx": 1,
            "specs": 1,
            "specsPow": 0,
            "blur": "Occasional strain after prolonged screen work",
            "smoke": 0,
            "alcohol": 0,
            "screen": "6–8 hours daily"
        }
    }

    print(f"\n[Step 2] Triggering BD Onboarding Flow (Simulating 'Save & Book' button click):")
    req = factory.post('/patient/api/onboard/', data=bd_onboarding_payload, content_type='application/json')
    view = OnboardPatientApiView.as_view()
    response = view(req)

    print(f"\n[Step 3] API Response Code: {response.status_code}")
    print("API Response Data:")
    for key, value in response.data.items():
        print(f"  • {key}: {value}")

    # Database Verification
    user_account = Optometrist.objects.filter(phone_number=dummy_mobile).first()
    patient_record = Patient.objects.filter(phone_number=dummy_mobile).first()

    print(f"\n[Step 4] Database Verification:")
    print(f"  • User Account Created in Auth Table: {'YES' if user_account else 'NO'}")
    if user_account:
        print(f"    - User ID: {user_account.id}")
        print(f"    - Role: {user_account.role}")
        print(f"    - Login Phone (Username): {user_account.phone_number}")

    print(f"  • Demographic Patient Record Created: {'YES' if patient_record else 'NO'}")
    if patient_record:
        print(f"    - Patient Account ID: {patient_record.patient_account_id}")
        print(f"    - Patient Name: {patient_record.name}")
        print(f"    - Email: {patient_record.email}")
        print(f"    - Risk Band: {patient.risk_band if 'patient' in locals() else patient_record.risk_band}")
        print(f"    - Payable Amount: INR {patient_record.payable_amount}")

    print("\n======================================================================")
    print("                   BD DASHBOARD TEST COMPLETE                        ")
    print("======================================================================")

if __name__ == "__main__":
    test_bd_dashboard_entry()
