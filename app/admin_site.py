from django.contrib.admin import AdminSite
from django.contrib.auth.admin import GroupAdmin, UserAdmin  # noqa: F401
from django.contrib.auth.models import Group, User


class SuperuserAdminSite(AdminSite):
    def has_permission(self, request):
        return request.user.is_active and request.user.is_superuser


admin_site = SuperuserAdminSite(name="scl_admin")


class SuperuserUserAdmin(UserAdmin):
    pass


class SuperuserGroupAdmin(GroupAdmin):
    pass


admin_site.register(User, SuperuserUserAdmin)
admin_site.register(Group, SuperuserGroupAdmin)

from financeiro.models import Cobranca, ConfiguracaoFinanceira, Pagamento  # noqa: E402

admin_site.register([ConfiguracaoFinanceira, Cobranca, Pagamento])

