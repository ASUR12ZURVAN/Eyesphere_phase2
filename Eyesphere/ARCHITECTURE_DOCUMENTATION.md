# EyeSphere Vision Wellness - System Architecture & Technical Documentation

## Executive Summary

EyeSphere Vision Wellness is a Django-based web application for eye health screening, patient management, and consultation services. The platform serves three primary user roles: patients, optometrists, and doctors, facilitating the complete patient journey from registration through screening to consultation.

---

## 1. Application Architecture

### 1.1 Overall Architecture Pattern

**Architecture Type**: Monolithic Django Application with REST API

**Frontend**: Django Templates (Server-Side Rendering) + JavaScript for dynamic interactions

**Backend**: Django 6.0.1 with Django REST Framework (DRF) 3.16.1

**API Style**: RESTful API with JWT Authentication

### 1.2 Application Flow

```
User (Patient/Optometrist/Doctor)
    ↓
Web Browser (Client)
    ↓
Django Application (Render)
    ↓
REST API Endpoints
    ↓
PostgreSQL Database (Neon Console)
    ↓
External Integrations (Google Calendar, Email SMTP)
```

### 1.3 Module Structure

The application is organized into three main Django apps:

- **optometrist**: User management, patient records, eye examinations, CMP records
- **patients**: Patient registration, screening tests, session requests, bookings
- **doctors**: Doctor dashboard, consultations, medication management

---

## 2. Database Platform & Configuration

### 2.1 Database Platform

**Primary Database**: PostgreSQL (via Neon Console)

**Development Database**: SQLite3 (local development)

**Database Service**: Neon Console (Serverless PostgreSQL)

**Connection Configuration**:
- Engine: `django.db.backends.postgresql`
- Connection Pooling: `conn_max_age=600` seconds
- SSL Required: `ssl_require=True`
- Environment Variable: `NEON_DB_URL` or `DATABASE_URL`

### 2.2 Database Hosting

**Production Database**: Hosted on Neon Console (cloud-based PostgreSQL)

**Development Database**: Local SQLite3 file (`db.sqlite3`)

**Database URL Configuration**:
```python
# Currently commented out in settings.py (lines 97-107)
# Production uses Neon Console via dj-database-url
DATABASES = {
    'default': dj_database_url.config(
        default=neon_db,
        conn_max_age=600,
        ssl_require=True
    )
}
```

---

## 3. Hosting & Cloud Infrastructure

### 3.1 Deployment Platform

**Primary Hosting**: Render (Third-party PaaS)

**Production URL**: `https://eyesphere-phase2-mpko.onrender.com`

**Domain**: `https://netrascreen.in` (CSRF trusted origin)

### 3.2 Infrastructure Components

- **Web Server**: Gunicorn (WSGI HTTP Server)
- **Static Files**: WhiteNoise (static file serving)
- **Process Management**: Render's built-in process management
- **SSL/TLS**: Provided by Render (HTTPS enabled)

### 3.3 Monitoring Services

- **Uptime Monitoring**: UptimeRobot (crash detection and uptime tracking)
- **Error Tracking**: Crashlytics setup (error reporting)

---

## 4. Database Schema & Relationships

### 4.1 Core Tables

#### **Optometrist** (User Model)
- **Purpose**: Central user model for all user types (patients, optometrists, doctors)
- **Primary Key**: `id` (Auto-increment)
- **Unique Identifier**: `phone_number` (USERNAME_FIELD)
- **Key Fields**:
  - `name`: Full name
  - `phone_number`: Unique phone number (login username)
  - `email`: Unique email (optional)
  - `role`: Enum ('optometrist', 'doctor', 'patient')
  - `designation`: Enum ('regular', 'corporate')
  - `license_number`: Professional license (optometrists/doctors)
  - `qualification`: Professional qualification
  - `coins`: Gamification points
  - `retention_time`: Total usage time in seconds
  - `is_active`, `is_staff`, `is_superuser`: Django permissions
  - `created_at`, `updated_at`: Timestamps

#### **Patient**
- **Purpose**: Detailed patient medical and demographic records
- **Primary Key**: `id` (Auto-increment)
- **Business Identifier**: `patient_account_id` (Format: ES-XXXXXX)
- **Key Fields**:
  - `name`, `age`, `gender`, `phone_number`, `address`
  - `login_type`: 'at_home' or 'corporate'
  - `company_name`, `designation`: Corporate details
  - **Medical History**: diabetes, hypertension, thyroid, family_history, steroid_use
  - **Eye History**: spectacles_use, last_checkup, blurred_vision, symptoms
  - **Lifestyle**: smoking, alcohol, screen_time, physical_activity
  - **Risk Assessment**: risk_score_raw, risk_score_pct, risk_band, urgency
  - **CMP Enrollment**: is_cmp_patient, cmp_type (cmp1/cmp2/cmp3)
  - **Booking Details**: primary_package, payable_amount, booking_date, booking_time
  - `created_at`, `updated_at`

#### **EyeExamination**
- **Purpose**: Comprehensive eye examination records
- **Primary Key**: `id` (Auto-increment)
- **Relationships**:
  - `patient`: ForeignKey to Patient
  - `optometrist`: ForeignKey to Optometrist (who conducted exam)
  - `consultant`: ForeignKey to Optometrist (doctor consultant)
- **Key Sections**:
  - Chief Complaints & History
  - Visual Acuity (RE/LE - uncorrected, pinhole, corrected)
  - Refraction (DV/NV - sph, cyl, axis, vision for both eyes)
  - Investigations (AR, refraction, Schirmer, TBUT, slit lamp, fundus, IOP)
  - Investigation Findings (numerical results)
  - Diagnosis & Advice (diagnosis_notes, provisional_diagnosis, advice)
  - `is_completed`: Boolean flag
  - `eye_health_rating`: Star rating (1-5)

#### **Medication**
- **Purpose**: Prescription medications for examinations
- **Primary Key**: `id` (Auto-increment)
- **Relationship**: `examination`: ForeignKey to EyeExamination
- **Fields**: name, quantity, frequency, eye, duration, instructions

#### **ScreeningTestResult**
- **Purpose**: Patient self-screening test results
- **Primary Key**: `id` (Auto-increment)
- **Relationship**: `user`: ForeignKey to Optometrist
- **Test Types**: vision, colorblind, dryeye, blink
- **Fields**: test_type, result_data (JSON), score, created_at

#### **OnlineSessionRequest"
- **Purpose**: Online consultation requests
- **Primary Key**: `id` (Auto-increment)
- **Relationships**: 
  - `user`: ForeignKey to Optometrist (patient)
  - `doctor`: ForeignKey to Optometrist (doctor consultant)
- **Fields**: status (pending/approved/rejected), scheduled_time, meet_link

#### **CMPRecord** (Chronic Management Program)
- **Purpose**: Clinical records for chronic condition management
- **Primary Key**: `id` (Auto-increment)
- **Relationships**:
  - `patient`: ForeignKey to Patient
  - `optometrist`: ForeignKey to Optometrist
- **CMP Types**: cmp1 (Standard Diabetic), cmp2 (Advanced Diabetic), cmp3 (Pediatric Myopia)
- **Fields**: 
  - Diabetic: hba1c_value, hba1c_report, kft_report, diabetes_type, medications
  - Pediatric: school_grade, axial_length, dilated_refraction, screen_time, outdoor_time
  - `recorded_at`: Timestamp

#### **UserLoginStat**
- **Purpose**: Activity tracking - monthly login frequency
- **Primary Key**: Composite (user, year_month)
- **Fields**: user, year_month (YYYY-MM format), login_count

#### **DailyUserUsage**
- **Purpose**: Daily usage time tracking
- **Primary Key**: Composite (user, date)
- **Fields**: user, date, total_seconds

#### **DailyTopTen**
- **Purpose**: Daily leaderboard snapshot
- **Primary Key**: date
- **Fields**: date, top_users_data (JSON)

#### **RedeemableService & RedemptionTicket**
- **Purpose**: Gamification - service redemption system
- **Fields**: name, description, coins_required, ticket_code, is_used

#### **HomeTestRequest**
- **Purpose**: Home visit test requests
- **Fields**: user, optometrist, phone_number, address, status

#### **PatientQuery**
- **Purpose**: Patient questions/queries
- **Fields**: user, name, phone_number, email, query_text

#### **AppointmentBooking**
- **Purpose**: Appointment scheduling
- **Fields**: user, booking_date, booking_time, tests (JSON), total_price

### 4.2 Entity Relationship Diagram

```
Optometrist (User Model)
├── Patient (1:N via phone_number matching)
│   ├── EyeExamination (1:N)
│   │   ├── Medication (1:N)
│   │   └── CMPRecord (1:N)
│   ├── ScreeningTestResult (1:N via user FK)
│   ├── OnlineSessionRequest (1:N via user FK)
│   ├── HomeTestRequest (1:N via user FK)
│   ├── PatientQuery (1:N via user FK)
│   └── AppointmentBooking (1:N via user FK)
├── EyeExamination (as optometrist) (1:N)
├── EyeExamination (as consultant) (1:N)
├── UserLoginStat (1:N)
├── DailyUserUsage (1:N)
└── RedemptionTicket (1:N)

RedeemableService
└── RedemptionTicket (1:N)
```

---

## 5. Patient ID & Unique Identifiers

### 5.1 Patient Identification System

**Primary Patient ID**: `patient_account_id`
- **Format**: ES-XXXXXX (e.g., ES-123456)
- **Generation**: Random 6-digit number prefixed with "ES-"
- **Uniqueness**: Unique per patient record
- **Usage**: Login username alternative, booking references, report identification

**User Account ID**: `id` (Optometrist model)
- **Format**: Auto-increment integer
- **Purpose**: Internal database primary key
- **Usage**: Foreign key relationships, JWT token subject

**Phone Number**: `phone_number`
- **Format**: 15-character string
- **Uniqueness**: Unique across all users
- **Purpose**: Primary login username, patient record matching

### 5.2 Record Linking Mechanism

**Patient to User Account Linking**:
- Patients are linked to user accounts via `phone_number` matching
- A single phone number can have multiple Patient records (different visits/onboarding)
- User account (Optometrist with role='patient') stores authentication credentials
- Patient records store detailed medical/demographic data

**Examination to Patient Linking**:
- Direct ForeignKey relationship from EyeExamination to Patient
- One patient can have multiple examinations over time

**User Activity Tracking**:
- UserLoginStat linked via Optometrist.id
- DailyUserUsage linked via Optometrist.id

---

## 6. Patient Journey Logic

### 6.1 Complete Patient Flow

```
1. REGISTRATION
   ↓
   Patient provides: name, phone, email, password, age, gender
   System creates: Optometrist account (role='patient') + Patient record
   Generates: patient_account_id (ES-XXXXXX)
   Sends: Email with credentials (if email provided)

2. ONBOARDING / SCREENING
   ↓
   Patient completes: Risk assessment questionnaire
   Captures: Medical history, eye history, lifestyle factors
   Calculates: Risk score, risk band, urgency level
   Recommends: Primary package, selected tests
   Records: Booking details (date, time, payable amount)

3. SCREENING TESTS (Self-Administered)
   ↓
   Vision Test (Snellen chart)
   Color Blindness Test
   Dry Eye Test (OSDI)
   Blink Rate Test
   Results stored in: ScreeningTestResult
   Rewards: 20 coins (once every 3 days)

4. EXAMINATION (Optometrist Conducted)
   ↓
   Optometrist creates: EyeExamination record
   Performs: Visual acuity, refraction, investigations
   Records: All examination findings
   Assigns: Doctor consultant (if needed)

5. CONSULTATION / REFERRAL
   ↓
   Doctor reviews: Examination findings + CMP records (if enrolled)
   Provides: Diagnosis, advice, medications
   Prescribes: Medication records
   Marks: is_completed = True

6. ONLINE SESSIONS (Alternative)
   ↓
   Patient requests: OnlineSessionRequest
   Doctor approves: Sets scheduled time
   System generates: Google Meet link via API
   Consultation conducted: Via video call

7. CHRONIC MANAGEMENT PROGRAM (CMP)
   ↓
   Patient enrolled: is_cmp_patient = True
   CMP type assigned: cmp1/cmp2/cmp3
   Optometrist records: Regular CMPRecord entries
   Tracks: Progression over time (append-only records)

8. HOME TEST REQUESTS
   ↓
   Patient requests: HomeTestRequest
   Optometrist assigned: For home visit
   Status tracked: pending → confirmed → completed

9. GAMIFICATION & REWARDS
   ↓
   Daily login: +10 coins
   Test completion: +20 coins (every 3 days)
   Coins redeemed: For services via RedemptionTicket
```

### 6.2 Key State Transitions

**Patient Registration**: New → Active (after account creation)

**Examination Status**: 
- Created → In Progress → Completed (when doctor finalizes)

**Session Request**: 
- Pending → Approved (with meet_link) → Rejected

**Home Test**: 
- Pending → Confirmed → Completed → Cancelled

**CMP Enrollment**: 
- Not Enrolled → Enrolled (is_cmp_patient=True) → Active Tracking

---

## 7. APIs & External Integrations

### 7.1 REST API Endpoints

#### **Patient APIs** (`/patient/`)
- `POST /patient/api/register/` - Patient registration
- `POST /patient/api/login/` - Patient login (JWT token)
- `POST /patient/api/onboard/` - Patient onboarding with risk assessment  //Not accessible through any UI 
- `POST /patient/api/save-screening-result/` - Save screening test results
- `GET /patient/api/screening-results/` - Get screening results
- `POST /patient/api/request-session/` - Request online consultation
- `POST /patient/api/book-home-test/` - Book home test
- `POST /patient/api/submit-query/` - Submit patient query
- `POST /patient/api/bookings/` - Create appointment booking
- `POST /patient/api/update-profile/` - Update patient profile
- `POST /patient/api/redeem-service/` - Redeem services with coins
- `GET /patient/pdf/screening/<pk>/` - Download screening PDF
- `GET /patient/pdf/exam/<pk>/` - Download examination PDF

#### **Optometrist APIs** (`/`)
- `POST /api/register/` - Optometrist registration
- `POST /api/login/` - Optometrist login
- `GET /api/list/` - List optometrists
- `GET /api/<pk>/` - Get optometrist details
- `POST /api/profile/update/` - Update profile
- `GET /api/corporate-patients/` - Get corporate patients (corporate optometrists only)
- `POST /api/exams/create/` - Create eye examination
- `GET /api/exams/<pk>/` - Get examination details
- `GET /api/exams/by-phone/<phone>/` - Get pending exam by phone
- `GET /api/patient-history/<phone>/` - Get patient examination history
- `GET /api/patient-info/<phone>/` - Get patient info by phone
- `POST /api/cmp/create/` - Create CMP clinical record
- `GET /api/cmp/history/<phone>/` - Get CMP history for patient

#### **Doctor APIs** (`/doctor/`)
- `POST /doctor/api/login/` - Doctor login
- `GET /doctor/api/list/` - List doctors
- `POST /doctor/schedule-session/<pk>/` - Schedule online session with Google Meet

### 7.2 External Integrations

#### **Google Calendar API**
- **Purpose**: Generate Google Meet links for online consultations
- **Library**: google-api-python-client, google-auth
- **Authentication**: OAuth 2.0 with refresh token
- **Environment Variables**:
  - `GOOGLE_CLIENT_ID`
  - `GOOGLE_CLIENT_SECRET`
  - `GOOGLE_REFRESH_TOKEN`
- **Function**: `create_meet_event()` in `google_calendar_utils.py`
- **Usage**: When doctor approves online session request

#### **Email SMTP Service**
- **Purpose**: Send patient credentials and notifications
- **Backend**: Django SMTP EmailBackend
- **Configuration**:
  - `EMAIL_HOST`: smtp.gmail.com (default)
  - `EMAIL_PORT`: 587
  - `EMAIL_USE_TLS`: True
  - `EMAIL_HOST_USER`: From environment
  - `EMAIL_HOST_PASSWORD`: From environment
- **Usage**: Registration confirmation, credential delivery

#### **Netrascreen Integration**
- **Purpose**: Branding and dashboard reference
- **Integration Level**: Branding/marketing integration (not API)
- **Usage**: Referenced in onboarding flow as "NetraScreen dashboard access"
- **Domain**: https://netrascreen.in (CSRF trusted origin)

---

## 8. Authentication & Access Control

### 8.1 Authentication Mechanism

**Primary Method**: JWT (JSON Web Tokens) via SimpleJWT

**Token Configuration**:
- **Access Token Lifetime**: 60 minutes
- **Refresh Token Lifetime**: 1 day
- **Algorithm**: HS256
- **Signing Key**: Django SECRET_KEY
- **Token Type Claim**: token_type
- **User ID Claim**: user_id

**Authentication Flow**:
1. User submits phone_number + password
2. Django `authenticate()` validates credentials
3. If valid, JWT tokens generated (access + refresh)
4. Session login also established for template views
5. Access token sent in Authorization header: `Bearer <token>`

**Login Methods**:
- Phone number + password (primary)
- Patient ID (ES-XXXXXX) + password (alternative)

### 8.2 User Roles & Permissions

#### **Role-Based Access Control**

**Three Primary Roles**:
1. **Patient** (`role='patient'`)
   - Can: Register, login, complete screening, view own results, request sessions
   - Cannot: Access optometrist/doctor dashboards, view other patients' data

2. **Optometrist** (`role='optometrist'`)
   - Can: Conduct examinations, view assigned patients, record CMP data
   - Sub-types: Regular vs Corporate (designation field)
   - Corporate optometrists: Can view corporate patient data

3. **Doctor** (`role='doctor'`)
   - Can: Consult on examinations, prescribe medications, approve sessions
   - Cannot: Create new examinations (optometrist role only)

#### **Permission Implementation**

**Django Built-in**:
- `is_staff`: Can access Django admin
- `is_superuser`: Full system access
- `is_active`: Account active status

**Custom Permissions** (via UserPassesTestMixin):
```python
# Example: Optometrist dashboard access
def test_func(self):
    return self.request.user.role == 'optometrist'

# Example: Corporate data access
if request.user.designation != 'corporate':
    return Response({'error': 'Unauthorized'}, status=403)
```

**API-Level Permissions**:
- `permissions.AllowAny`: Public endpoints (register, login)
- `permissions.IsAuthenticated`: Protected endpoints (requires valid JWT)
- Role checks in view logic for additional restrictions

### 8.3 Session Management

**Session Authentication**: Used alongside JWT for template views
- Django session middleware enabled
- CSRF protection enabled via CsrfExemptSessionAuth for API

**Token Refresh**:
- Refresh token rotation: Disabled
- Blacklist after rotation: Enabled (if rotation enabled)

---

## 9. Data Backup & Recovery Mechanism

### 9.1 Backup Strategy

**Primary Backup**: Neon Console Snapshots

**Backup Service**: Neon Console (PostgreSQL hosting provider)

**Snapshot Features**:
- Automated point-in-time snapshots
- Manual snapshot creation capability
- Snapshot restoration for disaster recovery
- Time-travel capability (query historical data)

### 9.2 Recovery Mechanism

**Recovery Process**:
1. Access Neon Console dashboard
2. Select database instance
3. Choose snapshot timestamp
4. Initiate restoration to new or existing database
5. Update application DATABASE_URL if needed

**Recovery Scope**:
- Full database restoration
- Table-level restoration (via Neon features)
- Point-in-time recovery (PITR)

### 9.3 Backup Frequency

**Automated Snapshots**: Configured via Neon Console (frequency not specified in code)

**Manual Backups**: Can be triggered via Neon Console UI or API

**Data Export**: Django `dumpdata` command available for manual exports

---

## 10. Data Security & Encryption

### 10.1 Data Encryption

**Database Encryption**:
- SSL/TLS required for database connections (`ssl_require=True`)
- Data encrypted in transit between app and database
- Neon Console provides at-rest encryption for PostgreSQL

**Password Security**:
- Passwords hashed using Django's PBKDF2 algorithm
- Salted hashing (automatic via Django)
- Password validators enforce complexity

**API Security**:
- JWT tokens signed with SECRET_KEY
- HTTPS enforced in production (Render provides SSL)
- CSRF protection for form submissions

### 10.2 Security Measures

**Environment Variables**:
- Sensitive data stored in environment variables
- SECRET_KEY, database URLs, email credentials not in code
- python-decouple library for configuration management

**CSRF Protection**:
- Django CSRF middleware enabled
- CSRF tokens required for POST requests
- Trusted origins configured for cross-origin requests

**Allowed Hosts**:
- `ALLOWED_HOSTS = ["*"]` (development)
- Production should restrict to specific domains

**CSRF Trusted Origins**:
- `https://eyesphere-phase2-mpko.onrender.com`
- `https://netrascreen.in`

### 10.3 Medical Data Protection

**Data Classification**:
- Patient medical history stored in database
- No explicit field-level encryption in current implementation
- Access controlled via authentication and role-based permissions

**Data Access**:
- Patients can only access their own data
- Optometrists can access assigned patient data
- Doctors can access referred patient data
- Admin access via Django admin panel

**Compliance Notes**:
- Consent mechanism referenced in compliance document
- Deletion mechanism required (not fully implemented in code)
- Audit logging: Basic login tracking via UserLoginStat

---

## 11. Audit Logs & Activity Tracking

### 11.1 Login Activity Tracking

**Model**: `UserLoginStat`

**Tracking Data**:
- User ID
- Year-Month (YYYY-MM format)
- Login count per month

**Implementation**:
```python
# Recorded on every patient login
stat, _ = UserLoginStat.objects.get_or_create(user=user, year_month=year_month)
stat.login_count += 1
stat.save()
```

### 11.2 Usage Time Tracking

**Model**: `DailyUserUsage`

**Tracking Data**:
- User ID
- Date
- Total seconds spent on platform

**Model**: `retention_time` (Optometrist model)
- Cumulative usage time in seconds
- Updated via `UpdateRetentionTimeView` API

### 11.3 Daily Leaderboard

**Model**: `DailyTopTen`

**Tracking Data**:
- Date
- Top 10 users snapshot (JSON)

**Purpose**: Gamification - daily rankings

### 11.4 Examination History

**Tracking Data**:
- All EyeExamination records with timestamps
- CMPRecord progression tracking (append-only)
- Medication history linked to examinations

### 11.5 Limitations

**Current Implementation**:
- Basic login frequency tracking
- No detailed action-level audit logs
- No IP address tracking
- No session duration logging
- No data modification audit trail

**Recommendations**:
- Implement Django Audit Log library
- Add IP address logging
- Track all CRUD operations on sensitive data
- Implement session duration tracking

---

## 12. Data Retention & Deletion Mechanism

### 12.1 Current Implementation

**Data Retention**:
- No automatic data deletion policies implemented
- All records retained indefinitely in database
- No data archival or purging mechanisms

**Data Deletion**:
- CASCADE deletes configured for foreign key relationships
- Manual deletion via Django admin
- No user-initiated self-deletion feature
- No anonymization procedures

### 12.2 Compliance Requirements

**Documented Requirements** (from Compliance and Improvement.md):
1. User consent mechanism
2. Deletion mechanism (required, not fully implemented)
3. [Third requirement not specified]

**Current Status**:
- Consent: Referenced but implementation unclear
- Deletion: Not implemented as user-facing feature
- Data retention: No defined policies

### 12.3 Recommendations

**Required Implementation**:
1. User account deletion request workflow
2. Data anonymization for retained records
3. Automated data retention policies (e.g., 7-year retention for medical records)
4. Right to be forgotten compliance
5. Data export functionality for users

---

## 13. User Roles & Permissions Summary

### 13.1 Role Matrix

| Feature | Patient | Optometrist | Doctor | Admin |
|---------|---------|-------------|--------|-------|
| Register/Login | ✓ | ✓ | ✓ | ✓ |
| View Dashboard | ✓ | ✓ | ✓ | ✓ |
| Complete Screening | ✓ | ✗ | ✗ | ✓ |
| View Own Results | ✓ | ✗ | ✗ | ✓ |
| Create Examination | ✗ | ✓ | ✗ | ✓ |
| Conduct Examination | ✗ | ✓ | ✗ | ✓ |
| Consult/Prescribe | ✗ | ✗ | ✓ | ✓ |
| View All Patients | ✗ | Limited* | Limited** | ✓ |
| Record CMP Data | ✗ | ✓ | ✗ | ✓ |
| Access Admin Panel | ✗ | ✗ | ✗ | ✓ |
| Corporate Data Access | ✗ | Corporate only | ✗ | ✓ |

*Optometrists view assigned patients; corporate optometrists view corporate patients
**Doctors view patients referred to them

### 13.2 Designation Types

**Optometrist Designations**:
- `regular`: Standard optometrist
- `corporate`: Corporate optometrist (can view corporate patient data)

**CMP Types**:
- `cmp1`: Standard Diabetic CMP
- `cmp2`: Advanced Diabetic CMP
- `cmp3`: Pediatric Myopia CMP

---

## 14. Medical Data Storage & Protection

### 14.1 Data Categories Stored

**Demographic Data**:
- Name, age, gender, phone, email, address
- Company name, designation (corporate patients)

**Medical History**:
- Systemic: diabetes, hypertension, thyroid, family history, steroid use
- Eye: spectacles use, last checkup, blurred vision, symptoms
- Lifestyle: smoking, alcohol, screen time, physical activity

**Clinical Data**:
- Visual acuity measurements (both eyes)
- Refraction data (sph, cyl, axis)
- Investigation results (Schirmer, TBUT, IOP, fundus)
- Diagnosis and advice
- Medication prescriptions

**CMP Data**:
- HbA1c values, diabetes medications
- Kidney disease status
- Pediatric: axial length, screen time, outdoor time
- Report file uploads (HbA1c, KFT reports)

### 14.2 Protection Measures

**Access Control**:
- Authentication required for all data access
- Role-based permissions restrict data visibility
- Patients can only access their own records
- Healthcare providers access only assigned patients

**Data in Transit**:
- SSL/TLS encryption for database connections
- HTTPS for all API communications
- JWT token authentication

**Data at Rest**:
- Neon Console provides encryption at rest
- No field-level encryption implemented
- Database access controlled via connection strings

**File Uploads**:
- Medical reports uploaded to media storage
- Access via authenticated URLs
- No explicit encryption for uploaded files

### 14.3 Data Privacy Considerations

**Identifiers**:
- Phone number as primary identifier
- Patient account ID (ES-XXXXXX) as business identifier - this feature has been implemented recently and doesn't affect the previous database records
- Email stored (optional)


**Sensitive Fields**:
- Medical conditions (boolean flags)
- Clinical measurements
- Prescription details

**Recommendations**:
- Implement field-level encryption for highly sensitive data
- Add data masking for non-essential views
- Implement audit logging for all data access
- Regular security audits
- Compliance with healthcare data regulations (HIPAA/GDPR as applicable)

---

## 15. Database Size & Records

### 15.1 Current Database Statistics

**Total Records**: ~111 records

**Record Breakdown**:
- Actual patient records: ~91
- Dummy/test records: ~20
- User accounts: Includes patients, optometrists, doctors
- Examination records: Varies per patient
- Screening results: Varies per patient

### 15.2 Record Distribution

**Patient Records**: ~91 active patients
**User Accounts**: Patients + Optometrists + Doctors
**Examinations**: One or more per patient
**Screening Results**: Multiple per patient (vision, colorblind, dryeye, blink)
**CMP Records**: For enrolled CMP patients only

### 15.3 Growth Considerations

**Current Scale**: Small-scale deployment (~100 records)
**Scalability**: PostgreSQL via Neon can handle significantly larger datasets
**Performance**: Current schema optimized for current scale
**Indexing**: Foreign keys indexed by default; additional indexes may be needed as scale grows

---

## 16. Technology Stack & Versions

### 16.1 Backend Framework

**Django**: 6.0.1
- Python web framework
- ORM, authentication, admin panel
- Template engine for server-side rendering

**Django REST Framework**: 3.16.1
- REST API toolkit
- Serializers, viewsets, permissions
- Integration with Django authentication

**Django REST Framework SimpleJWT**: 5.5.1
- JWT authentication backend
- Access and refresh token generation
- Token validation and rotation

### 16.2 Database & ORM

**PostgreSQL**: Via psycopg2-binary 2.9.11
- Primary production database
- Hosted on Neon Console

**SQLite3**: Local development database
- Django default for development

**Django ORM**: Built-in with Django
- Database abstraction layer
- Model definitions and migrations

**dj-database-url**: 3.1.2
- Database URL parsing
- Environment-based database configuration

### 16.3 Server & Deployment

**Gunicorn**: WSGI HTTP Server
- Production WSGI server
- Manages Django application processes

**WhiteNoise**: Static file serving
- Serves static files in production
- Compression and caching support

**Render**: PaaS Platform
- Application hosting
- SSL/TLS termination
- Process management

### 16.4 Authentication & Security

**PyJWT**: 2.11.0
- JWT token handling
- Token validation

**python-decouple**: 3.8
- Configuration management
- Environment variable parsing

**python-dotenv**: 1.2.1
- .env file support
- Environment variable loading

### 16.5 External Integrations

**Google APIs**:
- google-api-python-client: 2.194.0
- google-auth: 2.49.2
- google-auth-httplib2: 0.3.1
- google-auth-oauthlib: 1.3.1
- Purpose: Google Calendar API for Meet links

**Email**: Django built-in SMTP backend
- EmailMultiAlternatives for HTML emails
- SMTP configuration via environment variables

### 16.6 File Handling

**Pillow**: 12.1.0
- Image processing
- Profile picture uploads
- File upload handling

### 16.7 Development Tools

**Python Version**: Not specified in requirements (likely 3.12+ based on Django 6.0.1)

**Virtual Environment**: myenv (local development)

---

## 17. Production Database Hosting

### 17.1 Hosting Provider

**Provider**: Neon Console

**Service**: Serverless PostgreSQL

**Connection**: 
- URL configured via `NEON_DB_URL` or `DATABASE_URL` environment variable
- SSL required for all connections
- Connection pooling: 600-second max age

### 17.2 Neon Console Features

**Serverless Architecture**:
- Auto-scaling based on demand
- Pay-per-use pricing model
- No server management required

**Branching**:
- Database branching for development/testing
- Zero-copy branching for instant clones

**Time Travel**:
- Query historical data
- Point-in-time recovery
- Snapshot management

**Backup**:
- Automated snapshots
- Manual snapshot creation
- One-click restoration

**Performance**:
- Built connection pooling
- Edge caching
- Global edge network

### 17.3 Database Configuration

**Current Status**: 
- Neon configuration commented out in settings.py (lines 97-107)
- Currently using SQLite3 for local development
- Production deployment likely uses Neon via environment variables

**Configuration Code**:
```python
neon_db = config('NEON_DB_URL', default=config('DATABASE_URL', default=''))
DATABASES = {
    'default': dj_database_url.config(
        default=neon_db,
        conn_max_age=600,
        ssl_require=True
    )
}
```

---

## 18. Third-Party Services

### 18.1 Infrastructure Services

**Render** (Primary Hosting)
- Purpose: Application deployment and hosting
- Services: Web service, SSL/TLS, process management
- Cost: Freemium tier available
- URL: https://eyesphere-phase2-mpko.onrender.com

**Neon Console** (Database Hosting)
- Purpose: PostgreSQL database hosting
- Services: Serverless PostgreSQL, backups, time travel
- Cost: Pay-per-use pricing
- Features: Auto-scaling, branching, snapshots

### 18.2 Monitoring Services

**UptimeRobot**
- Purpose: Uptime monitoring and crash detection
- Service: Website monitoring, alerting
- Integration: Monitors Render deployment URL
- Purpose: Crashlytics setup for error tracking

### 18.3 Communication Services

**Google Calendar API**
- Purpose: Google Meet link generation
- Services: Calendar event creation, conference data
- Authentication: OAuth 2.0 with refresh token
- Usage: Online consultation scheduling

**SMTP Email Service**
- Purpose: Transactional email delivery
- Default: Gmail SMTP (smtp.gmail.com:587)
- Usage: Patient credentials, notifications
- Configuration: Via environment variables

### 18.4 Domain Services

**Netrascreen.in**
- Purpose: Branding domain
- Usage: CSRF trusted origin, patient portal URL
- Integration: Marketing/dashboard reference

### 18.5 Development Tools

**GitHub** (Inferred from .git presence)
- Purpose: Version control
- Repository: ASUR12ZURVAN/Eyesphere_phase2

**Python Package Index (PyPI)**
- Purpose: Package distribution
- Packages: All Python dependencies

---

## 19. Architecture & Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Patient    │  │ Optometrist  │  │    Doctor    │          │
│  │   Browser    │  │   Browser    │  │   Browser    │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                  │                  │                   │
│         └──────────────────┼──────────────────┘                   │
│                            │                                      │
└────────────────────────────┼──────────────────────────────────────┘
                             │ HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER (Render)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Django Application (Gunicorn)               │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │   │
│  │  │   Patients   │  │ Optometrist  │  │   Doctors    │    │   │
│  │  │     App      │  │     App      │  │     App      │    │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │   │
│  │         │                  │                  │            │   │
│  │  ┌──────┴──────────────────┴──────────────────┴──────┐    │   │
│  │  │         Django REST Framework (API Layer)          │    │   │
│  │  │  - JWT Authentication                              │    │   │
│  │  │  - Serializers                                     │    │   │
│  │  │  - Permissions                                     │    │   │
│  │  └──────┬───────────────────────────────────────────┘    │   │
│  │         │                                                 │   │
│  │  ┌──────┴───────────────────────────────────────────┐    │   │
│  │  │         Django ORM (Model Layer)                 │    │   │
│  │  │  - Optometrist, Patient, EyeExamination           │    │   │
│  │  │  - ScreeningTestResult, CMPRecord, etc.           │    │   │
│  │  └──────┬───────────────────────────────────────────┘    │   │
│  └─────────┼───────────────────────────────────────────────┘   │
│            │                                                     │
│  ┌─────────┴───────────────────────────────────────────────┐   │
│  │         Middleware & Security                             │   │
│  │  - CSRF Protection                                        │   │
│  │  - Session Management                                     │   │
│  │  - WhiteNoise (Static Files)                             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
└────────────────────────────┬──────────────────────────────────────┘
                             │ SSL/TLS
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATABASE LAYER (Neon)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              PostgreSQL Database                          │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │  Tables:                                                   │   │
│  │  - optometrist_optometrist (Users)                         │   │
│  │  - optometrist_patient                                     │   │
│  │  - optometrist_eyeexamination                              │   │
│  │  - optometrist_medication                                  │   │
│  │  - optometrist_cmprecord                                  │   │
│  │  - patients_screeningtestresult                           │   │
│  │  - patients_onlinesessionrequest                           │   │
│  │  - patients_hometestrequest                               │   │
│  │  - patients_appointmentbooking                            │   │
│  │  - patients_patientquery                                  │   │
│  │  - patients_redeemableservice                             │   │
│  │  - patients_redemptionticket                               │   │
│  │  - optometrist_userloginstat                               │   │
│  │  - optometrist_dailyuserusage                              │   │
│  │  - optometrist_dailytopten                                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │         Backup & Recovery (Neon Snapshots)                │   │
│  │  - Automated point-in-time snapshots                      │   │
│  │  - Manual snapshot creation                               │   │
│  │  - One-click restoration                                  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│  Google Calendar│  │  SMTP Email    │  │   Reports/     │
│      API        │  │    Service     │  │   Exports      │
│  (Meet Links)   │  │  (Gmail SMTP)  │  │  (PDF Downloads)│
└────────────────┘  └────────────────┘  └────────────────┘

         │
         ▼
┌────────────────┐
│  UptimeRobot   │
│  (Monitoring)  │
└────────────────┘
```

### Data Flow Summary

1. **User Request**: User accesses application via browser (HTTPS)
2. **Load Balancer**: Render routes request to Gunicorn
3. **Django Application**: 
   - Middleware processes request (CSRF, session)
   - URL routing directs to appropriate app/view
   - JWT authentication validates user
4. **Business Logic**: View processes request, calls models
5. **Database Operations**: ORM queries PostgreSQL via Neon
6. **External APIs**: 
   - Google Calendar API for Meet links
   - SMTP service for emails
7. **Response**: Data returned to user as JSON or HTML
8. **Static Files**: WhiteNoise serves static assets
9. **Monitoring**: UptimeRobot pings for uptime monitoring

---

## 20. Security Considerations & Recommendations

### 20.1 Current Security Strengths

- JWT-based authentication with token expiration
- SSL/TLS for database connections
- Role-based access control
- CSRF protection enabled
- Password hashing with salt
- Environment variable configuration

### 20.2 Security Gaps & Recommendations

**Immediate Actions**:
1. Restrict `ALLOWED_HOSTS` to specific domains instead of wildcard
2. Implement field-level encryption for sensitive medical data
3. Add rate limiting to API endpoints
4. Implement IP-based access logging
5. Add security headers (CSP, X-Frame-Options, etc.)

**Medium-Term**:
1. Implement comprehensive audit logging
2. Add data anonymization for non-production environments
3. Implement user self-deletion workflow
4. Add data retention policies
5. Implement session timeout and revocation

**Long-Term**:
1. HIPAA/GDPR compliance assessment
2. Regular security audits
3. Penetration testing
4. Implement SIEM integration
5. Add database encryption at rest (beyond Neon default)

### 20.3 Compliance Requirements

**Required**:
- User consent mechanism (partially implemented)
- Data deletion mechanism (not implemented)
- Audit logging (basic implementation)
- Data retention policies (not implemented)

**Recommended**:
- Privacy policy implementation
- Cookie consent mechanism
- Data processing agreements
- Data breach notification process
- Regular compliance audits

---

## 21. Performance & Scalability Considerations

### 21.1 Current Performance Characteristics

**Database Queries**:
- ORM queries with select_related/prefetch_related for optimization
- Foreign key indexes by default
- Connection pooling (600-second max age)

**Static Files**:
- WhiteNoise for efficient static file serving
- Compression enabled
- Manifest for cache busting

**Caching**:
- No explicit caching implementation
- Recommend Redis for session/data caching

### 21.2 Scalability Recommendations

**Database**:
- Neon auto-scales well for read-heavy workloads
- Consider read replicas for high read scenarios
- Implement database query optimization for complex queries

**Application**:
- Render auto-scales based on configuration
- Consider CDN for static assets
- Implement caching for frequently accessed data

**Monitoring**:
- Add application performance monitoring (APM)
- Implement database query monitoring
- Add error tracking beyond UptimeRobot

---

## 22. Deployment & DevOps

### 22.1 Deployment Process

**Current Deployment**: Render (PaaS)

**Deployment Steps** (Inferred):
1. Code pushed to Git repository
2. Render auto-deploys from main branch
3. Build process installs dependencies
4. Gunicorn starts application
5. Database migrations run
6. Static files collected

**Environment Variables Required**:
- `SECRET_KEY`
- `NEON_DB_URL` or `DATABASE_URL`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REFRESH_TOKEN`

### 22.2 CI/CD

**Current Status**: No explicit CI/CD pipeline configured

**Recommendations**:
- Add GitHub Actions for testing
- Automated testing before deployment
- Staging environment for pre-production testing
- Database migration automation

### 22.3 Monitoring & Alerting

**Current Monitoring**:
- UptimeRobot for uptime monitoring
- Render built-in metrics
- Basic error tracking

**Recommendations**:
- Add application logging (Sentry, LogRocket)
- Database performance monitoring
- Custom alerting rules
- Dashboard for key metrics

---

## 23. Documentation & Maintenance

### 23.1 Code Documentation

**Current State**:
- Basic docstrings in some functions
- Model field help text
- Limited inline comments

**Recommendations**:
- Comprehensive API documentation (Swagger/OpenAPI)
- Detailed docstrings for all functions
- Architecture decision records (ADRs)
- Onboarding documentation for developers

### 23.2 User Documentation

**Current State**:
- Patient credential emails with basic instructions
- Compliance document references
- No comprehensive user guides

**Recommendations**:
- Patient user guide
- Optometrist training manual
- Doctor consultation guide
- FAQ documentation
- Video tutorials

---

## 24. Future Enhancement Opportunities

### 24.1 Feature Enhancements

**Patient Experience**:
- Mobile application (React Native/Flutter)
- Push notifications for appointments
- Telemedicine integration improvements
- Payment gateway integration
- Appointment reminders

**Clinical Features**:
- Integration with EMR systems
- Advanced imaging upload (DICOM support)
- AI-powered risk assessment
- Treatment plan templates
- Prescription printing

**Administrative**:
- Advanced reporting and analytics
- Revenue tracking
- Inventory management
- Staff scheduling
- Multi-location support

### 24.2 Technical Enhancements

**Architecture**:
- Microservices migration (if scale requires)
- Event-driven architecture
- Message queue (Celery/Redis)
- GraphQL API alternative

**Data & Analytics**:
- Data warehouse implementation
- Business intelligence tools
- Predictive analytics
- Machine learning models

**Security**:
- Multi-factor authentication
- Biometric authentication
- Advanced threat detection
- Blockchain for audit trails

---

## 25. Contact & Support

**Application URL**: https://netrascreen.in/
**Application URL - Testing and production debugging**:https://eyesphere-phase2-mpko.onrender.com
**Patient Portal**: https://netrascreen.in/patient/api/login/
**Support Email**: support@eyesphere.com (from code)

**Development Team**:
- Repository: ASUR12ZURVAN/Eyesphere_phase2
- Technology Stack: Django 6.0.1, PostgreSQL, Neon Console, Render

---

## Appendix A: Environment Variables Reference

| Variable | Purpose | Required | Default |
|----------|---------|----------|---------|
| SECRET_KEY | Django secret key | Yes | (Hardcoded in dev) |
| NEON_DB_URL | Neon database URL | Yes (prod) | None |
| DATABASE_URL | Alternative database URL | No | None |
| EMAIL_HOST | SMTP host | No | smtp.gmail.com |
| EMAIL_PORT | SMTP port | No | 587 |
| EMAIL_USE_TLS | SMTP TLS | No | True |
| EMAIL_HOST_USER | SMTP username | Yes (email) | None |
| EMAIL_HOST_PASSWORD | SMTP password | Yes (email) | None |
| GOOGLE_CLIENT_ID | Google OAuth client ID | Yes (Meet) | None |
| GOOGLE_CLIENT_SECRET | Google OAuth secret | Yes (Meet) | None |
| GOOGLE_REFRESH_TOKEN | Google refresh token | Yes (Meet) | None |
| TIME_ZONE | Application timezone | No | UTC |

---

## Appendix B: API Endpoint Summary

### Patient Endpoints
- `POST /patient/api/register/` - Register patient
- `POST /patient/api/login/` - Login patient
- `POST /patient/api/onboard/` - Complete onboarding
- `POST /patient/api/save-screening-result/` - Save test result
- `GET /patient/api/screening-results/` - Get results
- `POST /patient/api/request-session/` - Request consultation
- `POST /patient/api/book-home-test/` - Book home test
- `POST /patient/api/submit-query/` - Submit query
- `POST /patient/api/bookings/` - Book appointment

### Optometrist Endpoints
- `POST /api/register/` - Register optometrist
- `POST /api/login/` - Login optometrist
- `GET /api/list/` - List optometrists
- `POST /api/exams/create/` - Create examination
- `GET /api/exams/by-phone/<phone>/` - Get exam by phone
- `GET /api/patient-history/<phone>/` - Get patient history
- `POST /api/cmp/create/` - Create CMP record
- `GET /api/cmp/history/<phone>/` - Get CMP history

### Doctor Endpoints
- `POST /doctor/api/login/` - Login doctor
- `GET /doctor/api/list/` - List doctors
- `POST /doctor/schedule-session/<pk>/` - Schedule session

---

**Document Version**: 1.0  
**Last Updated**: September 2026  
**Author**: System Analysis  
**Status**: Comprehensive Architecture Documentation
