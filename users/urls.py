from django.urls import path
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework_simplejwt.views import TokenRefreshView

from . import views
from .oauth_views import YandexOAuthView

yandex_oauth = YandexOAuthView()

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('token/', views.SocialTokenView.as_view(), name='social_token'),
    path(
        'token/refresh/',
        extend_schema_view(post=extend_schema(tags=['Авторизация']))(
            TokenRefreshView.as_view()
        )
    ),
    path('me/', views.AccountDetails.as_view(), name='account_details'),
    path('verify-email-link/', views.verify_email_link),
    path('delete/', views.user_delete, name='user_delete'),
    path(
        'social/select-type/',
        views.SelectUserTypeView.as_view(),
        name='select_user_type'
    ),
    path('social/yandex-oauth2/', yandex_oauth.authorize, name='yandex_auth'),
    path(
        'social/complete/yandex-oauth2/',
        yandex_oauth.complete,
        name='yandex_complete'
    ),
]
