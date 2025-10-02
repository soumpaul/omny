from django.urls import path
from .views import (
    DeviceRegistrationView,
    DeviceListView,
    DeviceDetailView,
    DeviceAlertCreateView,
    DeviceAlertListView,
    DeviceAlertAcknowledgeView,
    EmergencyEventCreateView,
    EmergencyEventListView,
    EmergencyEventRespondView,
)

app_name = 'devices'

urlpatterns = [
    # Device management
    path('register/', DeviceRegistrationView.as_view(), name='device-register'),
    path('', DeviceListView.as_view(), name='device-list'),
    path('<str:device_id>/', DeviceDetailView.as_view(), name='device-detail'),
    
    # Device alerts
    path('alerts/', DeviceAlertListView.as_view(), name='alert-list'),
    path('alerts/create/', DeviceAlertCreateView.as_view(), name='alert-create'),
    path('alerts/<int:alert_id>/acknowledge/', DeviceAlertAcknowledgeView.as_view(), name='alert-acknowledge'),
    
    # Emergency events
    path('emergencies/', EmergencyEventListView.as_view(), name='emergency-list'),
    path('emergencies/create/', EmergencyEventCreateView.as_view(), name='emergency-create'),
    path('emergencies/<int:emergency_id>/respond/', EmergencyEventRespondView.as_view(), name='emergency-respond'),
]
