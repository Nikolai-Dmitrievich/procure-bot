def save_social_profile(backend, user, response, *args, **kwargs):
    if backend.name == 'yandex-oauth2':
        user.is_social_user = True
        user.type = 'buyer'
        user.email_verified = True
        user.is_active = True
        user.save()
        print(f"Social User: {user.email} (is_social_user=True)")
    return None
