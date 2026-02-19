"""
Сериализаторы для аутентификации и управления пользователями.
Содержит LoginSerializer, RegisterSerializer и UserSerializer для работы
с системой пользователей ProcureBot.
"""

from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User


class LoginSerializer(serializers.Serializer):
    """Сериализатор для аутентификации пользователей по email/password"""
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, attrs):
        user = authenticate(
            username=attrs['email'],
            password=attrs['password']
        )
        if user and user.is_active:
            attrs['user'] = user
            return attrs
        raise serializers.ValidationError('Invalid email or password')


class RegisterSerializer(serializers.ModelSerializer):
    """
    Сериализатор для регистрации новых пользователей.
    Поддерживает типы: buyer (покупатель) и shop (магазин).
    Создает неактивного пользователя (требует верификации email).
    """
    password_confirm = serializers.CharField(write_only=True)
    type = serializers.ChoiceField(
        choices=[('buyer', 'Buyer'), ('shop', 'Shop')],
        default='buyer'
    )

    class Meta:
        model = User
        fields = (
            'first_name', 'last_name', 'email', 'username',
            'password', 'password_confirm', 'type'
        )

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError('Passwords do not match')
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')

        username = validated_data.get(
            'username',
            validated_data['email'].split('@')[0]
        )

        user = User(
            username=username,
            email=validated_data['email'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            type=validated_data.get('type', 'buyer'),
            is_active=False,
            is_staff=False,
            is_superuser=False,
            email_verified=False
        )
        user.set_password(password)
        user.save()

        return user


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения информации о пользователе"""
    is_active = serializers.BooleanField(default=False, read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'company', 'position', 'type', 'is_active', 'date_joined'
        ]
        read_only_fields = ['id', 'type', 'is_active']
