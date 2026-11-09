from django.db import models
from django.conf import settings
import uuid
import string
import random


class ScreeningTestResult(models.Model):
    TEST_TYPE_CHOICES = [
        ('vision', 'Vision Test (Snellen)'),
        ('colorblind', 'Color Blindness Test'),
        ('dryeye', 'Dry Eye (OSDI) Test'),
        ('blink', 'Blink Rate Test'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='screening_results'
    )
    test_type = models.CharField(max_length=20, choices=TEST_TYPE_CHOICES)
    result_data = models.JSONField(default=dict, help_text="Flexible JSON storage for test-specific results")
    score = models.CharField(max_length=100, blank=True, help_text="Human-readable score summary")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Screening Test Result"
        verbose_name_plural = "Screening Test Results"

    def __str__(self):
        return f"{self.user.name} - {self.get_test_type_display()} - {self.created_at.strftime('%d %b %Y')}"

class OnlineSessionRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='session_requests'
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='handled_session_requests',
        limit_choices_to={'role': 'doctor'}
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    scheduled_time = models.DateTimeField(null=True, blank=True)
    meet_link = models.URLField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Request from {self.user.name} - {self.status}"

class RedeemableService(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    coins_required = models.PositiveIntegerField()
    icon = models.CharField(max_length=50, default="🎁", help_text="Emoji or icon name")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class RedemptionTicket(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='redemption_tickets'
    )
    service = models.ForeignKey(
        RedeemableService,
        on_delete=models.CASCADE,
        related_name='tickets_generated'
    )
    ticket_code = models.CharField(max_length=20, unique=True, editable=False)
    redeemed_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-redeemed_at']

    def save(self, *args, **kwargs):
        if not self.ticket_code:
            self.ticket_code = self.generate_code()
        super().save(*args, **kwargs)

    def generate_code(self):
        prefix = "ES-"
        length = 8
        chars = string.ascii_uppercase + string.digits
        while True:
            code = prefix + ''.join(random.choices(chars, k=length))
            if not RedemptionTicket.objects.filter(ticket_code=code).exists():
                return code

    def __str__(self):
        return f"Ticket {self.ticket_code} - {self.service.name} by {self.user.name}"


class HomeTestRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='home_test_requests'
    )
    optometrist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assigned_home_tests',
        limit_choices_to={'role': 'optometrist'}
    )
    phone_number = models.CharField(max_length=15)
    email = models.EmailField()
    company_name = models.CharField(max_length=200, blank=True, null=True)
    address = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Home test for {self.user.name} - {self.status}"


class PatientQuery(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='queries'
    )
    name = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True, null=True)
    query_text = models.TextField(help_text="Patient's query (max 500 words)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Patient Query"
        verbose_name_plural = "Patient Queries"

    def __str__(self):
        return f"Query from {self.name} on {self.created_at.strftime('%d %b %Y')}"


class AppointmentBooking(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='appointment_bookings'
    )
    booking_date = models.DateField()
    booking_time = models.TimeField()
    tests = models.JSONField(help_text="Mapping of test names to prices")
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-booking_date', '-booking_time', '-created_at']

    def __str__(self):
        return f"Booking for {self.user.name} on {self.booking_date} at {self.booking_time}"
