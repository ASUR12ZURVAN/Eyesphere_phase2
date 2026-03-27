from django.db import models
from django.conf import settings


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
