from django.urls import path
from .views import RegisterOptometrist, LoginOptometrist, OptometristListView, OptometristDetailView

urlpatterns = [
    path('register/', RegisterOptometrist.as_view(), name='register'),
    path('login/', LoginOptometrist.as_view(), name='login'),
    path('list/', OptometristListView.as_view(), name='list'),
    path('<int:pk>/', OptometristDetailView.as_view(), name='detail'),
]
