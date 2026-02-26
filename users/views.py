import requests
from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiTypes,
    OpenApiParameter,
)
from rest_framework.decorators import api_view, permission_classes
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from .serializers import LoginSerializer, RegisterSerializer, SocialTokenSerializer, UserSerializer
from .models import User
from backend.services import redis_client
from django.conf import settings
from django.shortcuts import redirect
from rest_framework import status
from .serializers import LoginSerializer
from django.http import HttpResponseBadRequest
import logging


logger = logging.getLogger(__name__)
@extend_schema_view(
    post=extend_schema(
        tags=['Авторизация'],
        request=LoginSerializer,
        responses={200: OpenApiTypes.ANY}
    )
)
class LoginView(generics.GenericAPIView):
    """
    Аутентификация пользователя с JWT токенами.
    Проверяет email_verified для обычных пользователей.
    Staff/superuser получают токены без верификации.
    """
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        if user.is_staff or user.is_superuser:
            refresh = RefreshToken.for_user(user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            })

        if not user.email_verified:
            return Response({
                'error': 'Подтвердите email',
                'verify': 'Проверьте почту или запросите новый токен'
            }, status=400)

        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })


@extend_schema_view(
    post=extend_schema(
        tags=['Авторизация'],
        request=RegisterSerializer,
        responses={201: UserSerializer}
    )
)
class RegisterView(generics.CreateAPIView):
    """Регистрация нового пользователя с автоматической отправкой email"""
    serializer_class = RegisterSerializer
    queryset = User.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        from backend.tasks import send_email_verification
        send_email_verification.delay(user.id)

        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED
        )


@extend_schema_view(
    get=extend_schema(
        tags=['Авторизация'],
        responses={200: UserSerializer}
    ),
    patch=extend_schema(
        tags=['Авторизация'],
        request=UserSerializer,
        responses={200: OpenApiTypes.ANY}
    )
)
class AccountDetails(APIView):
    """Получение и обновление данных текущего пользователя"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UserSerializer(
            request.user,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({'status': True})
        return Response(serializer.errors, status=400)


@extend_schema(
    tags=['Авторизация'],
    parameters=[
        OpenApiParameter(
            name='token',
            type=str,
            location=OpenApiParameter.QUERY
            ),
        OpenApiParameter(
            name='email',
            type=str,
            location=OpenApiParameter.QUERY
            ),
    ]
)
@api_view(['GET'])
def verify_email_link(request):
    """
    Подтверждение email через GET ссылку из письма.
    Проверяет токен в Redis и активирует пользователя.
    """
    token = request.GET.get('token')
    email = request.GET.get('email')

    saved_token = redis_client.get(f"email_verify_{email}")
    if saved_token and saved_token == token:
        user = User.objects.get(email=email)
        user.email_verified = True
        user.is_active = True
        user.save()
        redis_client.delete(f"email_verify_{email}")
        return Response({'status': 'Email подтверждён'})

    return Response({'error': 'Недействительная ссылка'}, 400)


@extend_schema(tags=['Авторизация'])
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def user_delete(request):
    """Полное удаление аккаунта текущего пользователя"""
    request.user.delete()
    return Response({'status': 'Аккаунт удалён'}, status=200)



@extend_schema(tags=['Авторизация (Social)'])
@api_view(['GET'])
def yandex_auth(request):
    """Яндекс OAuth2 — ПРЯМЫЙ РЕДИРЕКТ НА ЯНДЕКС"""
    auth_url = (
        f"https://oauth.yandex.ru/authorize?"
        f"response_type=code&"
        f"client_id={settings.SOCIAL_AUTH_YANDEX_OAUTH2_KEY}&"
        f"redirect_uri={settings.SOCIAL_AUTH_YANDEX_OAUTH2_CALLBACK_URL}&"
        f"scope=login:email login:info"
    )
    return redirect(auth_url)


def yandexcomplete(request):
    """ПРЯМАЯ ЯНДЕКС OAUTH2 — CODE → JWT"""
    code = request.GET.get('code')
    logger.info(f"YANDEX CODE: {code}")
    
    if not code:
        return HttpResponseBadRequest('No code')
    
    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'client_id': settings.SOCIAL_AUTH_YANDEX_OAUTH2_KEY,
        'client_secret': settings.SOCIAL_AUTH_YANDEX_OAUTH2_SECRET,
    }
    
    token_resp = requests.post('https://oauth.yandex.ru/token', data=token_data).json()
    access_token = token_resp.get('access_token')
    
    if not access_token:
        logger.error(f"Token fail: {token_resp}")
        return HttpResponseBadRequest('Token exchange failed')

    user_info = requests.get(
        'https://login.yandex.ru/info', 
        params={'format': 'json', 'oauth_token': access_token}
    ).json()
    
    email = user_info.get('default_email') or user_info.get('emails', [None])[0]
    logger.info(f"Yandex user: {email}")

    user, created = User.objects.get_or_create(
        email=email,
        defaults={'username': email.split('@')[0], 'type': 'buyer', 
                 'is_social_user': True, 'is_active': True}
    )

    refresh = RefreshToken.for_user(user)
    return redirect(
        f"{settings.BASE_URL}/api/v1/auth/token/?social_email={email}"
    )


@extend_schema(
    tags=['Авторизация (Social)'],
    parameters=[
        OpenApiParameter(
            name='social_email',
            type=str,
            location=OpenApiParameter.QUERY,
            description='Email из Яндекс OAuth2 (user@yandex.ru)',
            required=True
        )
    ],
    responses={200: OpenApiTypes.ANY}
)
class SocialTokenView(APIView):
    """JWT для OAuth пользователей (GET/POST)"""
    serializer_class = SocialTokenSerializer
    
    def get(self, request):
        """GET: JWT по social_email из query params"""
        social_email = request.GET.get('social_email')
        
        if not social_email:
            return Response({'error': 'Требуется social_email'}, status=400)
        
        user = User.objects.filter(
            email=social_email,
            is_social_user=True,
            is_active=True
        ).first()
        
        if not user:
            return Response({'error': 'Соц. пользователь не найден'}, status=400)
        
        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {'email': user.email, 'type': user.type},
            'message': 'Вставьте ACCESS в Swagger → Authorize → Bearer {{token}}'
        })
    
    def post(self, request):
        """POST: JWT по social_email"""
        social_email = request.data.get('social_email')
        
        user = User.objects.filter(
            email=social_email,
            is_social_user=True,
            is_active=True
        ).first()

        if not user:
            return Response({'error': 'OAuth пользователь не найден'}, status=400)

        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token()),
            'refresh': str(refresh),
            'user': {'email': user.email, 'type': user.type}
        })
