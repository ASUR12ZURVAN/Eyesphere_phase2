from django.urls import path
from .views import (
    RegisterOptometrist, LoginOptometrist, OptometristListView, OptometristDetailView,
    OptometristDashboardPageView, LandingPageView, EyeExaminationCreateAPIView, NewExaminationPageView,
    EyeExaminationDetailView, ExaminationByPhoneView, PatientHistoryAPIView, PatientInfoByPhoneView
)

urlpatterns = [
    # API endpoints
    path('api/register/', RegisterOptometrist.as_view(), name='register_api'),
    path('api/login/', LoginOptometrist.as_view(), name='optometrist_login_page'),
    path('api/list/', OptometristListView.as_view(), name='list_api'),
    path('api/<int:pk>/', OptometristDetailView.as_view(), name='detail_api'),
    path('api/exams/create/', EyeExaminationCreateAPIView.as_view(), name='create_exam_api'),
    path('api/exams/<int:pk>/', EyeExaminationDetailView.as_view(), name='exam_detail_api'),
    path('api/exams/by-phone/<str:phone_number>/', ExaminationByPhoneView.as_view(), name='exam_by_phone_api'),
    path('api/patient-history/<str:phone_number>/', PatientHistoryAPIView.as_view(), name='patient_history_api'),
    path('api/patient-info/<str:phone_number>/', PatientInfoByPhoneView.as_view(), name='patient_info_api'),
    
    # Template pages
    path('', LandingPageView.as_view(), name='landing_page'),
    path('dashboard/', OptometristDashboardPageView.as_view(), name='optometrist_dashboard'),
    path('new-examination/', NewExaminationPageView.as_view(), name='new_examination_page'),
]
