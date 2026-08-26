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

def run_tests():
    print("=== Testing Automated Credential Email Workflow ===")
    factory = RequestFactory()
    
    # 1. Test BD / Patient Registration Endpoint
    test_mobile_1 = "9876500001"
    Optometrist.objects.filter(phone_number=test_mobile_1).delete()
    Patient.objects.filter(phone_number=test_mobile_1).delete()

    reg_payload = {
        "name": "Test Patient BD",
        "phone_number": test_mobile_1,
        "email": "test.patient.bd@example.com",
        "password": "SecurePassword123!",
        "age": 35,
        "gender": "male",
        "login_type": "corporate",
        "company_name": "Test Corp"
    }

    req1 = factory.post('/patient/api/register/', data=reg_payload, content_type='application/json')
    view1 = RegisterPatient.as_view()
    resp1 = view1(req1)
    
    print("\n[1] RegisterPatient Response:")
    print("Status Code:", resp1.status_code)
    print("Response Data:", resp1.data)
    
    assert resp1.status_code == 201
    assert resp1.data['status'] == 'success'
    assert 'patient_id' in resp1.data
    assert 'email_status' in resp1.data
    print("[PASS] RegisterPatient test passed!")

    # 2. Test OnboardPatientApiView Endpoint (Onboarding Dashboard)
    test_mobile_2 = "9876500002"
    Optometrist.objects.filter(phone_number=test_mobile_2).delete()
    Patient.objects.filter(phone_number=test_mobile_2).delete()

    onboard_payload = {
        "p_name": "Test Patient Onboarding",
        "p_mobile": test_mobile_2,
        "email": "test.patient.onboard@example.com",
        "age": 45,
        "gender": "female",
        "riskPct": 42,
        "riskBand": "Moderate risk",
        "urgency": "Consultation recommended within 2 weeks",
        "primaryPackage": "Comprehensive Vision & Diabetic Retinopathy Care",
        "payable": 1499.00,
        "booking_code": "BK-998877",
        "booking_date": "2026-08-30",
        "booking_time": "10:30 AM"
    }

    req2 = factory.post('/patient/api/onboard/', data=onboard_payload, content_type='application/json')
    view2 = OnboardPatientApiView.as_view()
    resp2 = view2(req2)

    print("\n[2] OnboardPatientApiView Response:")
    print("Status Code:", resp2.status_code)
    print("Response Data:", resp2.data)

    assert resp2.status_code == 201
    assert resp2.data['status'] == 'success'
    assert resp2.data['patient_name'] == 'Test Patient Onboarding'
    assert 'patient_id' in resp2.data
    assert 'password' in resp2.data
    assert 'email_status' in resp2.data
    print("[PASS] OnboardPatientApiView test passed!")

    print("\n=======================================================")
    print("ALL TESTS PASSED SUCCESSFULLY! Workflow fully verified.")

if __name__ == "__main__":
    run_tests()
