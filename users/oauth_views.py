"""Базовые классы для OAuth2 провайдеров"""

import logging
import secrets
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import requests
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User
from users.oauth_config import OAUTH_PROVIDERS, OAuthProvider

logger = logging.getLogger(__name__)


class BaseOAuthView(ABC):
    """
    Базовый класс для OAuth2 провайдеров.

    Flow:
    1. authorize() - редирект на провайдера за authorization code
    2. complete() - обработка callback, exchange code на token, получение user info
    """

    provider_name: str
    redirect_pattern: str = '{base_url}/api/v1/auth/token/?social_email={email}'
    state_ttl: int = 300

    @property
    def provider(self) -> OAuthProvider:
        """Получение конфигурации провайдера"""

        try:
            return OAUTH_PROVIDERS[self.provider_name]
        except KeyError:
            raise ValueError(f"Unknown OAuth provider: {self.provider_name}")

    def get_client_id(self) -> str:
        """Получение client_id из настроек"""

        env_var = f'{self.provider_name.upper()}_CLIENT_ID'
        return getattr(settings, env_var, '')

    def get_client_secret(self) -> str:
        """Получение client_secret из настроек"""

        env_var = f'{self.provider_name.upper()}_CLIENT_SECRET'
        return getattr(settings, env_var, '')

    def get_redirect_uri(self) -> str:
        """Получение redirect_uri из настроек"""

        env_var = f'{self.provider_name.upper()}_REDIRECT_URI'
        return getattr(settings, env_var, '')

    def authorize(self, request):
        """
        Шаг 1: Редирект на провайдера для авторизации.
        Генерирует state токен для CSRF защиты.
        """

        state = secrets.token_urlsafe(32)
        cache.set(f"oauth_state_{state}", True, self.state_ttl)

        auth_url = (
            f"{self.provider.authorize_url}?"
            f"response_type=code&"
            f"client_id={self.get_client_id()}&"
            f"redirect_uri={self.get_redirect_uri()}&"
            f"scope={self.provider.scope}&"
            f"state={state}"
        )
        return redirect(auth_url)

    def complete(self, request):
        """
        Шаг 2: Callback от провайдера.
        - Проверяет state (CSRF защита)
        - Обменивает code на access_token
        - Получает user info
        - Создаёт/находит пользователя
        - Редиректит на страницу с JWT токеном
        """

        code = request.GET.get('code')
        state = request.GET.get('state')
        error = request.GET.get('error')

        if error:
            logger.error(f"{self.provider_name} OAuth error: {error}")
            return self.handle_error('OAuth provider returned error')

        if not code:
            return HttpResponseBadRequest('No authorization code')

        if state:
            saved_state = cache.get(f"oauth_state_{state}")
            if not saved_state:
                logger.warning(f"{self.provider_name} OAuth: Invalid state")
                return HttpResponseBadRequest('Invalid state')
            cache.delete(f"oauth_state_{state}")

        try:
            token_response = self._exchange_code(code)
            access_token = token_response.get('access_token')

            if not access_token:
                logger.error(
                    f"{self.provider_name} OAuth: No access_token in response"
                )
                return self.handle_error('Token exchange failed', token_response)

            user_info = self._get_user_info(access_token)
            email = self._extract_email(user_info)

            if not email:
                logger.error(
                    f"{self.provider_name} OAuth: No email in user_info"
                )
                return self.handle_error('No email from provider', user_info)

            user = self._get_or_create_user(email, user_info)

            token = secrets.token_urlsafe(32)
            cache.set(f"oauth_temp_token_{token}", user.id, 300)

            logger.info(
                f"{self.provider_name} OAuth: User authenticated: {email}"
            )

            redirect_url = (
                f"{settings.BASE_URL}"
                f"{self.provider.redirect_after_auth}"
                f"?token={token}&email={email}"
            )
            return redirect(redirect_url)

        except requests.RequestException as e:
            logger.error(f"{self.provider_name} OAuth request error: {str(e)}")
            return self.handle_error(f'OAuth error: {str(e)}', {})
        except Exception as e:
            logger.error(
                f"{self.provider_name} OAuth unexpected error: {str(e)}"
            )
            return self.handle_error(f'Unexpected error: {str(e)}', {})

    def _exchange_code(self, code: str) -> Dict[str, Any]:
        """Обмен authorization code на access token"""

        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': self.get_client_id(),
            'client_secret': self.get_client_secret(),
            'redirect_uri': self.get_redirect_uri(),
        }

        response = requests.post(
            self.provider.token_url,
            data=data,
            timeout=10,
            headers=self.provider.token_headers or {'Accept': 'application/json'}
        )
        response.raise_for_status()
        return response.json()

    def _get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Получение информации о пользователе"""

        url = self.provider.user_info_url

        headers = (
            dict(self.provider.user_info_headers)
            if self.provider.user_info_headers else {}
        )
        if 'Authorization' not in headers and 'yandex' not in self.provider_name:
            headers['Authorization'] = f'Bearer {access_token}'

        params = (
            dict(self.provider.user_info_params)
            if self.provider.user_info_params else {}
        )
        if 'yandex' in self.provider_name:
            params['oauth_token'] = access_token

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    def _extract_email(self, user_info: Dict[str, Any]) -> str:
        """Извлечение email из ответа провайдера"""

        if self.provider_name == 'github':
            emails = user_info.get('emails', [])
            primary = next(
                (e for e in emails if e.get('primary')),
                emails[0] if emails else {}
            )
            return primary.get('email', '') if isinstance(primary, dict) else ''

        email_field = self.provider.user_info_email_field
        email = user_info.get(email_field)

        if not email and self.provider_name == 'google':
            email = user_info.get('email')

        return email or ''

    def _get_or_create_user(self, email: str, user_info: Dict[str, Any]) -> User:
        """Создание или поиск пользователя"""

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email.split('@')[0],
                'type': 'buyer',
                'is_social_user': True,
                'is_active': True,
            }
        )

        if created:
            logger.info(f"{self.provider_name} OAuth: Created user {email}")
        else:
            logger.info(f"{self.provider_name} OAuth: Found user {email}")

        return user

    def handle_error(self, message: str, context: Dict) -> redirect:
        """Обработка ошибок с редиректом на страницу логина"""

        error_url = f"{settings.BASE_URL}/login?error=oauth_failed"
        return redirect(error_url)


class YandexOAuthView(BaseOAuthView):
    """OAuth2 провайдер для Яндекс"""

    provider_name = 'yandex'
