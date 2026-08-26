# Testing Guide: Automated Patient Credential Emails

This guide details how to test the automated patient credential email system across the **Onboarding Dashboard**, **BD / Patient Registration Dashboard**, and backend API endpoints.

---

## 📋 Overview of the Automated Email Workflow

Whenever a patient account is created or onboarded:
1. **Account Credentials Generated**: System assigns a unique Patient ID (`ES-XXXXXX`), sets the mobile number as the username, and generates/retains a password.
2. **Automated Dispatch**: Django's `EmailMultiAlternatives` constructs a dual HTML + plain-text email containing:
   - **Account Number / Patient ID**
   - **Login Mobile (Username)**
   - **Password**
   - **Patient Portal Link** (`https://netrascreen.in/patient/api/login/`)
   - **Vision Risk & Assessment Summary** *(For Onboarding completions)*
3. **Delivery / Logging**: If live SMTP is configured in `.env`, the email is delivered to the patient's inbox. If placeholder SMTP credentials are present in local development, the full email details are logged to the Django console.

---

## ⚙️ Step 1: Configuring Email Delivery Settings (`.env`)

Depending on whether you are running a **Live Inbox Test** or a **Console Log Test**, verify your `phase2/.env` file:

### Option A: Testing Live Inbox Delivery (Gmail SMTP)
To receive real emails in your inbox, update your `.env` file with an **App Password**:
```env
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_16_character_app_password
DEFAULT_FROM_EMAIL=EyeSphere Support <your_email@gmail.com>
```
> [!NOTE]
> For Gmail, generate a 16-character App Password at [Google Account Security → 2-Step Verification → App Passwords](https://myaccount.google.com/apppasswords).

### Option B: Local Console Testing (No External SMTP Needed)
Leave `EMAIL_HOST_USER=your_email@gmail.com` as default. The backend detects placeholder credentials and logs the formatted email directly to your server terminal output without delaying API responses.

---

## 🧪 Step 2: Running the Automated Test Script (Fastest Method)

We have provided an automated test script that tests both the BD registration endpoint and Onboarding API endpoint.

1. Open your terminal in the `phase2` directory.
2. Run the test script:
   ```bash
   python scratch/test_credential_email_workflow.py
   ```
3. **Expected Terminal Output**:
   ```text
   === Testing Automated Credential Email Workflow ===
   [MAIL LOG] Automated Credential Email generated for Test Patient BD (test.patient.bd@example.com):
   Subject: Welcome to EyeSphere - Your Patient Credentials & Vision Report [ES-XXXXXX]
   Patient ID: ES-XXXXXX
   Username: 9876500001
   Password: SecurePassword123!
   
   [1] RegisterPatient Response:
   Status Code: 201
   [PASS] RegisterPatient test passed!

   [2] OnboardPatientApiView Response:
   Status Code: 201
   [PASS] OnboardPatientApiView test passed!
   
   =======================================================
   ALL TESTS PASSED SUCCESSFULLY! Workflow fully verified.
   ```

---

## 🌐 Step 3: Interactive UI Testing

### Test A: Onboarding Dashboard Workflow (`/patient/onboard/`)

1. **Start Django Server**:
   ```bash
   python manage.py runserver
   ```
2. Navigate to: `http://127.0.0.1:8000/patient/onboard/`
3. Fill in the **Basic Patient Information**:
   - **Name**: e.g., `Jane Doe`
   - **Mobile**: e.g., `9876543210`
   - **Email Address**: Enter your real email address to test live inbox delivery.
4. Complete the assessment questions and select a screening package.
5. Click **"Save Record"** or **"Onboard Patient"**.
6. **Expected Results**:
   - A modal dialog appears titled **"Patient Onboarded Successfully"**.
   - Displays **Patient ID**, **Mobile Username**, **Generated Password**, and **Email Status**.
   - Check the email inbox (or Django server console) for the welcome email with credentials & vision summary.

---

### Test B: BD Dashboard / Patient Registration (`/patient/register/`)

1. Navigate to: `http://127.0.0.1:8000/patient/register/`
2. Select **Corporate Login** or **At Home Login**.
3. Fill in the form:
   - **Full Name**: `Corporate Test User`
   - **Phone Number**: `9812345678`
   - **Email Address**: `user@example.com`
   - **Password**: `TestPass123`
   - **Age**: `30`, **Gender**: `Male`
   - *(If Corporate)* **Company Name**: `Acme Corp`
4. Click **"Create Account"**.
5. **Expected Results**:
   - Alert notification: `"Account created successfully!"`.
   - Page redirects to sign-in page.
   - Credentials email is dispatched immediately to the registered email address.

---

## 🛠️ Step 4: API Testing via cURL / Postman

### Endpoint 1: BD Patient Registration (`POST /patient/api/register/`)
```bash
curl -X POST http://127.0.0.1:8000/patient/api/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "API Test Patient",
    "phone_number": "9112233445",
    "email": "testapi@example.com",
    "password": "Password123!",
    "age": 28,
    "gender": "male",
    "login_type": "at_home"
  }'
```
**Expected Response Status**: `201 Created`
```json
{
  "message": "Account created successfully!",
  "status": "success",
  "patient_id": "ES-123456",
  "user": {
    "id": 42,
    "name": "API Test Patient",
    "phone_number": "9112233445",
    "email": "testapi@example.com",
    "patient_account_id": "ES-123456"
  },
  "email_sent": true,
  "email_status": "Credentials emailed successfully to testapi@example.com."
}
```

---

### Endpoint 2: Onboarding Completion (`POST /patient/api/onboard/`)
```bash
curl -X POST http://127.0.0.1:8000/patient/api/onboard/ \
  -H "Content-Type: application/json" \
  -d '{
    "p_name": "Onboard API Patient",
    "p_mobile": "9988776655",
    "email": "onboardtest@example.com",
    "age": 50,
    "gender": "female",
    "riskPct": 55,
    "riskBand": "Moderate risk",
    "urgency": "Routine checkup",
    "primaryPackage": "Comprehensive Vision Care",
    "payable": 1200.00
  }'
```
**Expected Response Status**: `201 Created`
```json
{
  "status": "success",
  "message": "Patient successfully onboarded and backend record created!",
  "patient_id": "ES-654321",
  "patient_name": "Onboard API Patient",
  "phone_number": "9988776655",
  "email": "onboardtest@example.com",
  "password": "ES@aB3xD",
  "is_new_user": true,
  "email_sent": true,
  "email_status": "Credentials emailed successfully to onboardtest@example.com."
}
```

---

## 🔍 Step 5: Verification Checklist

- [x] **Account Number Assigned**: `patient_account_id` field is populated on `Patient` model.
- [x] **Optometrist User Model Synchronized**: Account created with `role='patient'`.
- [x] **Email Subject Line**: Contains Patient Account ID `[ES-XXXXXX]`.
- [x] **Email Content**: Includes Patient ID, Username (Mobile), Password, and Portal Link.
- [x] **Error Resiliency**: If SMTP fails or email is invalid, account creation completes successfully without throwing server 500 errors.
