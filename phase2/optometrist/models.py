from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class OptometristManager(BaseUserManager):
    def create_user(self, phone_number, name, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('The Phone Number must be set')
        user = self.model(phone_number=phone_number, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(phone_number, name, password, **extra_fields)

class Optometrist(AbstractBaseUser, PermissionsMixin):
    name = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    role = models.CharField(
        max_length=20,
        choices=[('optometrist', 'Optometrist'), ('doctor', 'Doctor'), ('patient', 'Patient')],
        default='optometrist'
    )

    # Professional fields (Admin editable only via admin.py logic if preferred)
    license_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    qualification = models.CharField(max_length=200, blank=True, null=True, help_text="e.g., Doctor of Optometry (OD)")
    specialization = models.CharField(max_length=200, blank=True, null=True, help_text="e.g., Pediatric Optometry, Contact Lenses")
    experience_years = models.PositiveIntegerField(default=0)
    bio = models.TextField(blank=True, null=True)
    clinic_address = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='optometrists/', blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    office_hours = models.CharField(max_length=200, blank=True, null=True, help_text="e.g., Mon-Fri: 9am-5pm")
    languages = models.CharField(max_length=200, blank=True, null=True, help_text="e.g., English, Spanish")
    
    # Corporate related fields
    designation = models.CharField(
        max_length=20,
        choices=[('regular', 'Regular Optometrist'), ('corporate', 'Corporate Optometrist')],
        default='regular'
    )
    working_hospital = models.CharField(max_length=200, blank=True, null=True)
    assigned_companies = models.TextField(blank=True, null=True, help_text="Comma-separated list of company names they work with")
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Gamification Fields
    coins = models.IntegerField(default=0)
    last_coin_login_date = models.DateField(null=True, blank=True)
    last_coin_test_date = models.DateField(null=True, blank=True)

    # Usage Monitoring
    retention_time = models.PositiveIntegerField(default=0, help_text="Total usage time in seconds")

    objects = OptometristManager()

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['name']

    def __str__(self):
        return f"{self.name} ({self.phone_number})"

    class Meta:
        verbose_name = "Optometrist"
        verbose_name_plural = "Optometrists"
        ordering = ['-created_at']

class Patient(models.Model):
    name = models.CharField(max_length=200)
    age = models.PositiveIntegerField()
    gender = models.CharField(
        max_length=10,
        choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')]
    )
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    
    # New Registration Details
    login_type = models.CharField(
        max_length=20,
        choices=[('at_home', 'At Home Login'), ('corporate', 'Corporate Login')],
        default='at_home'
    )
    company_name = models.CharField(max_length=200, blank=True, null=True)
    designation = models.CharField(max_length=200, blank=True, null=True)

    # Onboarding Contact & Location Details
    email = models.EmailField(blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    location_other = models.CharField(max_length=100, blank=True, null=True)
    age_group = models.CharField(max_length=20, blank=True, null=True)

    # Systemic Medical History
    diabetes = models.BooleanField(default=False)
    diabetes_over_5yrs = models.BooleanField(default=False)
    hba1c_level = models.CharField(max_length=50, blank=True, null=True)
    hypertension = models.BooleanField(default=False)
    thyroid = models.BooleanField(default=False)
    family_history = models.BooleanField(default=False)
    steroid_use = models.BooleanField(default=False)

    # Eye & Vision Health History
    spectacles_use = models.BooleanField(default=False)
    spectacles_power_high = models.BooleanField(default=False)
    last_checkup = models.CharField(max_length=50, blank=True, null=True)
    blurred_vision = models.CharField(max_length=50, blank=True, null=True)
    symptoms = models.TextField(blank=True, null=True)

    # Lifestyle Factors
    smoking = models.BooleanField(default=False)
    alcohol = models.BooleanField(default=False)
    screen_time = models.CharField(max_length=50, blank=True, null=True)
    physical_activity = models.CharField(max_length=50, blank=True, null=True)

    # Vision Risk & Assessment Score Output
    risk_score_raw = models.IntegerField(default=0)
    risk_score_pct = models.IntegerField(default=0)
    risk_band = models.CharField(max_length=50, blank=True, null=True)
    urgency = models.CharField(max_length=100, blank=True, null=True)
    conversion_likelihood = models.CharField(max_length=50, blank=True, null=True)
    disease_top3 = models.JSONField(default=list, blank=True, null=True)
    selected_tests = models.TextField(blank=True, null=True)

    # Package Deal & Booking Details
    primary_package = models.CharField(max_length=150, blank=True, null=True)
    free_basic = models.BooleanField(default=False)
    add_on_people = models.JSONField(default=list, blank=True, null=True)
    people_count = models.IntegerField(default=1)
    payable_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    mrp_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    savings_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tele_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    ta_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    manual_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    referral_code = models.CharField(max_length=50, blank=True, null=True)
    booking_code = models.CharField(max_length=50, blank=True, null=True)
    booking_date = models.CharField(max_length=50, blank=True, null=True)
    booking_time = models.CharField(max_length=50, blank=True, null=True)
    optometrist_assigned = models.CharField(max_length=150, blank=True, null=True)
    special_notes = models.TextField(blank=True, null=True)
    patient_account_id = models.CharField(max_length=50, blank=True, null=True)
    raw_answers = models.JSONField(default=dict, blank=True, null=True)

    risk_factor = models.CharField(
        max_length=20, 
        choices=[
            ('not_classified', 'Not Classified'),
            ('low', 'Low Risk'), 
            ('moderate', 'Moderate Risk'), 
            ('high', 'High Risk')
        ], 
        default='not_classified',
        help_text="Categorize patients based on risk for future segregation"
    )
    is_cmp_patient = models.BooleanField(default=False, help_text="Whether this patient is enrolled in a Chronic Management Program (CMP)")
    cmp_type = models.CharField(
        max_length=10,
        choices=[
            ('cmp1', 'CMP1 - Standard Diabetic CMP'),
            ('cmp2', 'CMP2 - Advanced Diabetic CMP'),
            ('cmp3', 'CMP3 - Pediatric Myopia CMP'),
        ],
        blank=True,
        null=True,
        help_text="The CMP program the patient is enrolled under (set during onboarding)",
    )
    has_received_reward = models.BooleanField(default=False, help_text="Track if patient received coins for completing profile")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.age}/{self.gender})"


class EyeExamination(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='examinations')
    optometrist = models.ForeignKey(Optometrist, on_delete=models.CASCADE, related_name='exams_conducted', limit_choices_to={'role': 'optometrist'})
    consultant = models.ForeignKey(Optometrist, on_delete=models.SET_NULL, null=True, blank=True, related_name='exams_consulted', limit_choices_to={'role': 'doctor'})
    date_of_visit = models.DateField(auto_now_add=True)
    
    # 1. Chief Complaints and History
    chief_complaints = models.TextField(blank=True)
    systemic_history = models.TextField(blank=True, default="NA")
    screen_time = models.CharField(max_length=100, blank=True)
    history_eye_disease = models.TextField(blank=True, default="NA")
    history_eye_surgery = models.TextField(blank=True, default="NA")
    
    # 2. Visual Acuity
    # Right Eye (RE)
    uncorrected_vision_re = models.CharField(max_length=20, blank=True)
    pinhole_vision_re = models.CharField(max_length=20, blank=True)
    corrected_vision_re = models.CharField(max_length=20, blank=True)
    # Left Eye (LE)
    uncorrected_vision_le = models.CharField(max_length=20, blank=True)
    pinhole_vision_le = models.CharField(max_length=20, blank=True)
    corrected_vision_le = models.CharField(max_length=20, blank=True)
    
    # 3. Refraction
    # DV (Distance Vision) - RE
    dv_sph_re = models.CharField(max_length=10, blank=True)
    dv_cyl_re = models.CharField(max_length=10, blank=True)
    dv_axis_re = models.CharField(max_length=10, blank=True)
    dv_vision_re = models.CharField(max_length=10, blank=True)
    # DV - LE
    dv_sph_le = models.CharField(max_length=10, blank=True)
    dv_cyl_le = models.CharField(max_length=10, blank=True)
    dv_axis_le = models.CharField(max_length=10, blank=True)
    dv_vision_le = models.CharField(max_length=10, blank=True)
    # Add NV (Near Vision) - RE
    nv_sph_re = models.CharField(max_length=10, blank=True)
    nv_cyl_re = models.CharField(max_length=10, blank=True)
    nv_axis_re = models.CharField(max_length=10, blank=True)
    nv_vision_re = models.CharField(max_length=10, blank=True)
    # Add NV - LE
    nv_sph_le = models.CharField(max_length=10, blank=True)
    nv_cyl_le = models.CharField(max_length=10, blank=True)
    nv_axis_le = models.CharField(max_length=10, blank=True)
    nv_vision_le = models.CharField(max_length=10, blank=True)
    
    # 4. Investigations Performed (True/False)
    performed_ar_assessment = models.BooleanField(default=False)
    performed_refraction = models.BooleanField(default=False)
    performed_schirmer = models.BooleanField(default=False)
    performed_tbut = models.BooleanField(default=False)
    performed_slit_lamp = models.BooleanField(default=False)
    performed_fundus = models.BooleanField(default=False)
    performed_iop = models.BooleanField(default=False)
    
    # 5. Investigation Findings
    schirmer_re = models.CharField(max_length=50, blank=True)
    schirmer_le = models.CharField(max_length=50, blank=True)
    tbut_re = models.CharField(max_length=50, blank=True)
    tbut_le = models.CharField(max_length=50, blank=True)
    slit_lamp_re = models.CharField(max_length=100, blank=True, default="NORMAL")
    slit_lamp_le = models.CharField(max_length=100, blank=True, default="NORMAL")
    fundus_re = models.CharField(max_length=100, blank=True)
    fundus_le = models.CharField(max_length=100, blank=True)
    iop_re = models.CharField(max_length=50, blank=True)
    iop_le = models.CharField(max_length=50, blank=True)
    
    # 6. Diagnosis & Advice
    diagnosis_notes = models.TextField(blank=True, help_text="Doctor's detailed observations and notes")
    provisional_diagnosis = models.TextField(blank=True)
    advice = models.TextField(blank=True)
    
    is_completed = models.BooleanField(default=False, help_text="Set to True when the doctor finalizes consultation")
    
    eye_health_rating = models.IntegerField(blank=True, null=True, help_text="Star rating out of 5")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Exam for {self.patient.name} on {self.date_of_visit}"

class Medication(models.Model):
    examination = models.ForeignKey(EyeExamination, on_delete=models.CASCADE, related_name='medications')
    name = models.CharField(max_length=200)
    quantity = models.CharField(max_length=50, blank=True)
    frequency = models.CharField(max_length=100)
    eye = models.CharField(
        max_length=20,
        choices=[('Both eyes', 'Both eyes'), ('Right eye', 'Right eye'), ('Left eye', 'Left eye'), ('-', '-')],
        default='Both eyes'
    )
    duration = models.CharField(max_length=100)
    instructions = models.TextField(blank=True)
    
    def __str__(self):
        return self.name

class UserLoginStat(models.Model):
    user = models.ForeignKey(Optometrist, on_delete=models.CASCADE, related_name='login_stats')
    year_month = models.CharField(max_length=7, help_text="Format: YYYY-MM")
    login_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('user', 'year_month')
        verbose_name = "User Login Stat"
        verbose_name_plural = "User Login Stats"

    def __str__(self):
        return f"{self.user.name} - {self.year_month}: {self.login_count}"


class DailyTopTen(models.Model):
    date = models.DateField(unique=True)
    top_users_data = models.JSONField(default=list, help_text="Stores a snapshot of the top 10 users for this day")

    class Meta:
        verbose_name = "Daily Top Ten"
        verbose_name_plural = "Daily Top Tens"
        ordering = ['-date']


class DailyUserUsage(models.Model):
    user = models.ForeignKey(Optometrist, on_delete=models.CASCADE, related_name='daily_usages')
    date = models.DateField()
    total_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Daily User Usage"
        verbose_name_plural = "Daily User Usages"
        ordering = ['-date', '-total_seconds']
        unique_together = ('user', 'date')


class CMPRecord(models.Model):
    CMP_TYPES = [
        ('cmp1', 'CMP1 - Standard Diabetic CMP'),
        ('cmp2', 'CMP2 - Advanced Diabetic CMP'),
        ('cmp3', 'CMP3 - Pediatric Myopia CMP'),
    ]
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='cmp_records')
    optometrist = models.ForeignKey(
        Optometrist,
        on_delete=models.SET_NULL,
        related_name='cmp_records_entered',
        limit_choices_to={'role': 'optometrist'},
        blank=True,
        null=True,
        help_text='Optometrist who recorded this entry',
    )
    cmp_type = models.CharField(max_length=10, choices=CMP_TYPES)
    hba1c_value = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True, help_text='HbA1c value (%)')
    hba1c_report = models.FileField(upload_to='cmp/hba1c_reports/', blank=True, null=True)
    kft_report = models.FileField(upload_to='cmp/kft_reports/', blank=True, null=True)
    diabetes_type = models.CharField(max_length=10, choices=[('type1', 'Type 1'), ('type2', 'Type 2')], blank=True, null=True)
    current_diabetes_medications = models.TextField(blank=True, null=True)
    has_kidney_disease = models.BooleanField(blank=True, null=True, help_text='Presence of kidney disease (Yes/No)')
    exercise_frequency = models.CharField(max_length=100, blank=True, null=True)
    school_grade = models.CharField(max_length=50, blank=True, null=True)
    axial_length = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True)
    dilated_refraction = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    avg_daily_screen_time = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    avg_daily_outdoor_time = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    eye_muscle_status = models.CharField(max_length=200, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'CMP Clinical Record'
        verbose_name_plural = 'CMP Clinical Records'
        ordering = ['-recorded_at']
