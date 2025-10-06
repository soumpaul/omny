from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from .views import (
    RegisterView,
    LoginView,
    VerifyTokenView,
    UserProfileView,
    LogoutView,
)

app_name = 'authentication'

urlpatterns = [
    path('register/', csrf_exempt(RegisterView.as_view()), name='register'),
    path('login/', csrf_exempt(LoginView.as_view()), name='login'),
    path('verify-token/', csrf_exempt(VerifyTokenView.as_view()), name='verify'),
    path('profile/', csrf_exempt(UserProfileView.as_view()), name='profile'),
    path('logout/', csrf_exempt(LogoutView.as_view()), name='logout'),
]
