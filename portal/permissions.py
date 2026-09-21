from functools import wraps

from django.core.exceptions import PermissionDenied


def group_required(*names):
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            allowed = request.user.is_superuser or request.user.groups.filter(
                name__in=names
            ).exists()
            if not allowed:
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapped
    return decorator
