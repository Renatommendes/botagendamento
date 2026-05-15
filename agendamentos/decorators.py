from django.contrib.auth.decorators import user_passes_test

def super_admin_required(view_func):
    def check(user):
        return user.is_authenticated and user.is_superuser
    return user_passes_test(check)(view_func)