from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Панель управления пользователями с аватаром (Baton совместимо)
    """

    fieldsets = (
        (None, {'fields': ('email', 'password', 'type')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'company', 'position', 'avatar')}),
        ('Дополнительно', {'fields': ('email_verified', 'is_social_user')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Дополнительно', {
            'fields': ('company', 'position', 'type', 'email_verified', 'is_social_user', 'avatar'),
            'classes': ('wide',)
        }),
    )

    list_display = ('email', 'first_name', 'last_name', 'type', 'company', 'is_staff', 'email_verified', 'get_avatar_preview',)
    list_filter = ['type', 'email_verified', 'is_social_user', 'is_staff', 'is_active']
    search_fields = ['email', 'first_name', 'last_name', 'company', 'position']

    readonly_fields = ['avatar_preview']

    def get_avatar_preview(self, obj):
        """Круглая аватарка 38x38 в списке"""
        if obj.avatar and obj.avatar.url:
            return format_html(
                '<img src="{}" style="width:38px;height:38px;border-radius:50%;object-fit:cover;border:1px solid #ddd;">',
                obj.avatar.url
            )
        return 'Нет аватара'
    get_avatar_preview.short_description = 'Аватар'

    def avatar_preview(self, obj):
        """Превью 200px в форме редактирования"""
        if obj.avatar and obj.avatar.url:
            return format_html(
                '<img src="{}" style="max-height:200px;max-width:200px;border-radius:10px;border:1px solid #ddd;">',
                obj.avatar.url
            )
        return 'Загрузите аватар (120x120 JPG рекомендуем)'
    avatar_preview.short_description = 'Превью аватара'
