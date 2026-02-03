from django.urls import path
from .views import (
    RegisterOptometrist, LoginOptometrist, OptometristListView, OptometristDetailView,
    OptometristLoginPageView, OptometristRegisterPageView, OptometristDashboardPageView
)

urlpatterns = [
    # API endpoints
    path('api/register/', RegisterOptometrist.as_view(), name='register_api'),
    path('api/login/', LoginOptometrist.as_view(), name='login_api'),
    path('api/list/', OptometristListView.as_view(), name='list_api'),
    path('api/<int:pk>/', OptometristDetailView.as_view(), name='detail_api'),
    
    # Template pages
    path('login/', OptometristLoginPageView.as_view(), name='optometrist_login_page'),
    path('register/', OptometristRegisterPageView.as_view(), name='optometrist_register_page'),
    path('dashboard/', OptometristDashboardPageView.as_view(), name='optometrist_dashboard'),
]
