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
    