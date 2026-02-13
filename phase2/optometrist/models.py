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
        choices=[('optometrist', 'Optometrist'), ('doctor', 'Doctor')],
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
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
    