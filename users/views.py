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
from .serializers import LoginSerializer, RegisterSerializer, UserSerializer
from .models import User
from backend.services import redis_client


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
