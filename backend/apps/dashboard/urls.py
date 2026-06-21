from django.urls import path
from .views import DashboardOverviewView

app_name = 'dashboard'

urlpatterns = [
    path('overview/', DashboardOverviewView.as_view(), name='overview'),
]
