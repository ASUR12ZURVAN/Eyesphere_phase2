import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'phase2.settings')
django.setup()

from optometrist.models import Optometrist, DailyUserUsage, DailyTopTen
from django.utils import timezone
from django.db.models import F

def test_metrics():
    # 1. Setup a test user
    phone = '9999999999'
    user, created = Optometrist.objects.get_or_create(
        phone_number=phone,
        defaults={'name': 'Test User', 'role': 'patient'}
    )
    
    # 2. Simulate UpdateRetentionTimeView logic
    elapsed = 120 # 2 minutes
    
    Optometrist.objects.filter(pk=user.pk).update(
        retention_time=F('retention_time') + elapsed
    )
    
    today = timezone.localdate()
    usage, created = DailyUserUsage.objects.get_or_create(user=user, date=today)
    usage.total_seconds = F('total_seconds') + elapsed
    usage.save(update_fields=['total_seconds'])
    
    # Simulate the top ten update
    top_users = DailyUserUsage.objects.filter(date=today).order_by('-total_seconds')[:10]
    top_users_data = []
    top_users_list = list(top_users.select_related('user'))
    for tu in top_users_list:
        top_users_data.append({
            'user_id': tu.user.id,
            'name': tu.user.name,
            'phone_number': tu.user.phone_number,
            'total_seconds': tu.total_seconds
        })
    
    daily_top, _ = DailyTopTen.objects.get_or_create(date=today)
    daily_top.top_users_data = top_users_data
    daily_top.save(update_fields=['top_users_data'])
    
    print("Metrics updated successfully.")
    
    # 3. Simulate PlatformTimeMetricsView logic
    from patients.views import PlatformTimeMetricsView
    from rest_framework.test import APIRequestFactory, force_authenticate
    
    factory = APIRequestFactory()
    request = factory.get('/api/metrics/usage/')
    force_authenticate(request, user=user)
    
    view = PlatformTimeMetricsView.as_view()
    response = view(request)
    
    print("Response Status Code:", response.status_code)
    print("Response Data:", response.data)

if __name__ == '__main__':
    test_metrics()
