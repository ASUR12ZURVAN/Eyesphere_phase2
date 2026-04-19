import os
import sys
import django

# Add current directory to path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'phase2.settings')
django.setup()

from optometrist.models import Optometrist, Patient

def create_data():
    # 1. Create Optometrist
    optom_phone = "1234567890"
    optom_pass = "password123"
    
    if not Optometrist.objects.filter(phone_number=optom_phone).exists():
        optom = Optometrist.objects.create_user(
            phone_number=optom_phone,
            name="Dr. Test Optom",
            password=optom_pass,
            role='optometrist',
            working_hospital="City Eye Hospital",
            assigned_companies="Google, Microsoft"
        )
        print(f"Created Optometrist: {optom_phone}")
    else:
        optom = Optometrist.objects.get(phone_number=optom_phone)
        optom.set_password(optom_pass)
        optom.role = 'optometrist'
        optom.save()
        print(f"Updated Optometrist: {optom_phone}")

    # 2. Create Corporate Patients
    patients_data = [
        {"name": "Alice Green", "phone": "9876543210", "company": "Google", "age": 28, "gender": "female"},
        {"name": "Bob Smith", "phone": "9876543211", "company": "Google", "age": 35, "gender": "male"},
        {"name": "Charlie Brown", "phone": "9876543212", "company": "Microsoft", "age": 42, "gender": "male"},
        {"name": "Diana Ross", "phone": "9876543213", "company": "Apple", "age": 31, "gender": "female"},
    ]

    for p in patients_data:
        patient, created = Patient.objects.update_or_create(
            phone_number=p['phone'],
            defaults={
                "name": p['name'],
                "age": p['age'],
                "gender": p['gender'],
                "login_type": 'corporate',
                "company_name": p['company'],
                "address": f"123 {p['company']} HQ"
            }
        )
        print(f"{'Created' if created else 'Updated'} Patient: {p['name']} ({p['company']})")

    # 3. Save credentials to file
    with open('test_credentials.txt', 'w') as f:
        f.write("=== EYE SPHERE TEST CREDENTIALS ===\n\n")
        f.write("OPTOMETRIST ACCOUNT:\n")
        f.write(f"Phone: {optom_phone}\n")
        f.write(f"Password: {optom_pass}\n\n")
        f.write("CORPORATE PATIENTS:\n")
        for p in patients_data:
            f.write(f"- {p['name']} (Company: {p['company']}, Phone: {p['phone']})\n")
    
    print("\nCredentials saved to test_credentials.txt")

if __name__ == "__main__":
    create_data()
