import logging

from django.conf import settings
from django.shortcuts import redirect
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
    extend_schema_view,
)
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from backend.services import redis_client
from users.models import User
from users.serializers import (
    LoginSerializer,
    RegisterSerializer,
    SocialTokenSerializer,
    UserSerializer,
)

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
    throttle_classes = [AnonRateThrottle]

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
    throttle_classes = [AnonRateThrottle]

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
            return Response(
                {'error': 'Соц. пользователь не найден'},
                status=400
            )

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
            return Response(
                {'error': 'OAuth пользователь не найден'},
                status=400
            )

        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token()),
            'refresh': str(refresh),
            'user': {'email': user.email, 'type': user.type}
        })


class SelectUserTypeView(APIView):
    """Выбор типа пользователя после OAuth авторизации"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Авторизация (Social)'],
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'type': {
                        'type': 'string',
                        'enum': ['buyer', 'shop'],
                        'example': 'buyer'
                    }
                },
                'required': ['type']
            }
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'access': {'type': 'string'},
                    'refresh': {'type': 'string'},
                    'user': {
                        'type': 'object',
                        'properties': {
                            'email': {'type': 'string'},
                            'type': {'type': 'string'},
                            'is_social_user': {'type': 'boolean'}
                        }
                    }
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'}
                }
            }
        }
    )
    def post(self, request):
        """Установка типа пользователя (buyer или shop)"""

        user_type = request.data.get('type')

        if user_type not in ['buyer', 'shop']:
            return Response(
                {'error': 'Тип должен быть buyer или shop'},
                status=400
            )

        request.user.type = user_type
        request.user.save()

        refresh = RefreshToken.for_user(request.user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'email': request.user.email,
                'type': request.user.type,
                'is_social_user': request.user.is_social_user
            }
        })
