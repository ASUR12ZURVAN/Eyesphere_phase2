from django.urls import path
from .views import RegisterPatient, LoginPatient, PatientDashboardView

urlpatterns = [
    # Template pages
    path('', PatientDashboardView.as_view(), name='patient_dashboard'),
    path('api/login/', LoginPatient.as_view(), name='patient_login_page'),
    path('api/register/', RegisterPatient.as_view(), name='patient_register_page'),
]
