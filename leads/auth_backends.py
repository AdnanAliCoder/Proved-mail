from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

class EmailBackend(ModelBackend):
    """Authenticate via email while retaining Django's standard password hashing."""
    def authenticate(self, request, username=None, password=None, **kwargs):
        email = (kwargs.get("email") or username or "").strip()
        if not email or password is None:
            return None
        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(email__iexact=email)
        except UserModel.DoesNotExist:
            # Run a password hash to reduce timing differences for unknown accounts.
            UserModel().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
