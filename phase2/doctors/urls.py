from django.urls import path
from .views import LoginDoctor, DoctorDashboardPageView, DoctorListView
from django.views.generic import RedirectView

urlpatterns = [
    # Template pages
    path('', DoctorDashboardPageView.as_view(), name='doctor_dashboard'),
    path('api/login/', LoginDoctor.as_view(), name='doctor_login_page'),

    # API endpoints
    path('api/list/', DoctorListView.as_view(), name='doctor_list_api'),
    path('dashboard/', RedirectView.as_view(pattern_name='doctor_dashboard', permanent=True)),
]
