from django.urls import path
from .views import (
    RegisterPatient, LoginPatient, PatientDashboardView,
    VisionTestView, ColorBlindTestView, OSDITestView, BlinkTestView,
    SaveScreeningResultView, PatientLogoutView, RequestOnlineSessionView,
    DownloadScreeningPDFView, DownloadExamPDFView, UpdateRetentionTimeView,
    UpdatePatientProfileView, RedeemServiceView, GetOptometristsView, BookHomeTestView, GetPatientProfileView
)

urlpatterns = [
    # Template pages
    path('', PatientDashboardView.as_view(), name='patient_dashboard'),
    path('api/login/', LoginPatient.as_view(), name='patient_login_page'),
    path('api/register/', RegisterPatient.as_view(), name='patient_register_page'),
    path('logout/', PatientLogoutView.as_view(), name='patient_logout'),

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
    path('api/update-profile/', UpdatePatientProfileView.as_view(), name='update_patient_profile'),
    path('api/redeem-service/', RedeemServiceView.as_view(), name='redeem_service'),
    path('api/get-optometrists/', GetOptometristsView.as_view(), name='get_optometrists'),
    path('api/book-home-test/', BookHomeTestView.as_view(), name='book_home_test'),
    path('api/get-profile/', GetPatientProfileView.as_view(), name='get_patient_profile_api'),
]
