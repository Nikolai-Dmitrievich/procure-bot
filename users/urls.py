from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView
    )
from drf_spectacular.utils import extend_schema_view, extend_schema
from . import views

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('token/', extend_schema_view(post=extend_schema(tags=['Авторизация']))(TokenObtainPairView.as_view()), ),
    path('token/refresh/', extend_schema_view(
        post=extend_schema(tags=['Авторизация'])
    )(TokenRefreshView.as_view())),
    path('me/', views.AccountDetails.as_view(), name='account_details'),
    path('verify-email-link/', views.verify_email_link),
    path('delete/', views.user_delete, name='user_delete'),
]
