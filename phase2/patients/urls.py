from django.urls import path
from .views import (
    RegisterPatient, LoginPatient, PatientDashboardView,
    VisionTestView, ColorBlindTestView, OSDITestView, BlinkTestView,
    SaveScreeningResultView, patient_logout, RequestOnlineSessionView,
    DownloadScreeningPDFView, DownloadExamPDFView, UpdateRetentionTimeView
)

urlpatterns = [
    # Template pages
    path('', PatientDashboardView.as_view(), name='patient_dashboard'),
    path('api/login/', LoginPatient.as_view(), name='patient_login_page'),
    path('api/register/', RegisterPatient.as_view(), name='patient_register_page'),
    path('logout/', patient_logout, name='patient_logout'),

    # Screening test pages
    path('screening/vision/', VisionTestView.as_view(), name='patient_vision_test'),
    path('screening/colorblind/', ColorBlindTestView.as_view(), name='patient_colorblind_test'),
    path('screening/osdi/', OSDITestView.as_view(), name='patient_osdi_test'),
    path('screening/blink/', BlinkTestView.as_view(), name='patient_blink_test'),

    # API endpoints
    path('api/save-screening-result/', SaveScreeningResultView.as_view(), name='save_screening_result'),
    path('api/request-session/', RequestOnlineSessionView.as_view(), name='request_online_session'),
    path('api/update-retention/', UpdateRetentionTimeView.as_view(), name='update_retention_time'),
    
    # PDF downloads
    path('pdf/screening/<int:pk>/', DownloadScreeningPDFView.as_view(), name='download_screening_pdf'),
    path('pdf/exam/<int:pk>/', DownloadExamPDFView.as_view(), name='download_exam_pdf'),
]

