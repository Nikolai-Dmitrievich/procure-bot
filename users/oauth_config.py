"""Конфигурация OAuth2 провайдеров"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class OAuthProvider:
    """Конфигурация OAuth2 провайдера"""

    name: str
    authorize_url: str
    token_url: str
    user_info_url: str
    user_info_email_field: str
    scope: str
    token_headers: Optional[Dict[str, str]] = None
    user_info_headers: Optional[Dict[str, str]] = None
    user_info_params: Optional[Dict[str, str]] = None
    redirect_after_auth: str = '/api/v1/auth/social/select-type/'


OAUTH_PROVIDERS: Dict[str, OAuthProvider] = {
    'yandex': OAuthProvider(
        name='yandex',
        authorize_url='https://oauth.yandex.ru/authorize',
        token_url='https://oauth.yandex.ru/token',
        user_info_url='https://login.yandex.ru/info',
        user_info_email_field='default_email',
        scope='login:email login:info',
        user_info_params={'format': 'json'},
    ),
}
