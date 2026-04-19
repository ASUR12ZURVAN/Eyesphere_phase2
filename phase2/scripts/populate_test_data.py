import os
import sys
import django
import random
import string

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'phase2.settings')
django.setup()

from optometrist.models import Optometrist, Patient
from django.contrib.auth import get_user_model

User = get_user_model()

def generate_random_phone():
    return ''.join(random.choices(string.digits, k=10))

def populate_data():
    companies = ["Google", "Microsoft", "Meta", "Amazon", "Apple"]
    passwords = ["Pass123!", "Test@2024", "Secure#99"]
    
    test_credentials = []

    # 1. Create Optometrists
    optometrists_data = [
        {"name": "Dr. Rahul Sharma", "phone": "9876543210", "companies": "Google,Microsoft,Meta"},
        {"name": "Dr. Anjali Verma", "phone": "8765432109", "companies": "Amazon,Apple,Google"}
    ]

    for opto in optometrists_data:
        user, created = User.objects.get_or_create(
            phone_number=opto['phone'],
            defaults={
                'name': opto['name'],
                'role': 'optometrist',
                'assigned_companies': opto['companies']
            }
        )
        password = "Password@123"
        user.set_password(password)
        user.is_active = True
        user.save()
        test_credentials.append(f"Optometrist: {opto['name']} | Phone: {opto['phone']} | Password: {password}")

    # 2. Create Corporate Patients
    for i in range(1, 16):
        name = f"Patient {i}"
        phone = f"70000000{i:02d}"
        company = random.choice(companies)
        password = "PatientPass123"
        
        # Create User account
        user, created = User.objects.get_or_create(
            phone_number=phone,
            defaults={
                'name': name,
                'role': 'patient',
                'email': f"patient{i}@example.com"
            }
        )
        user.set_password(password)
        user.is_active = True
        user.save()
        
        # Create Patient record
        Patient.objects.update_or_create(
            phone_number=phone,
            defaults={
                'name': name,
                'age': random.randint(20, 60),
                'gender': random.choice(['male', 'female']),
                'login_type': 'corporate',
                'company_name': company,
                'designation': random.choice(['Software Engineer', 'Manager', 'Analyst', 'HR'])
            }
        )
        test_credentials.append(f"Patient ({company}): {name} | Phone: {phone} | Password: {password}")

    # Write credentials to file
    credentials_file = 'test_credentials.txt'
    with open(credentials_file, 'w') as f:
        f.write("\n".join(test_credentials))
    
    print(f"Successfully created 2 optometrists and 15 corporate patients.")
    print(f"Credentials saved to {credentials_file}")

if __name__ == "__main__":
    populate_data()
