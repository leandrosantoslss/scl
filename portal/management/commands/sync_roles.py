from django.apps import apps
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from portal.roles import ROLE_PERMISSION_PREFIXES


SCL_APPS = {"licencas", "portal", "financeiro", "integracoes", "licenciamento"}

DEFAULT_PREFIXES = ("add_", "change_", "delete_", "view_")


class Command(BaseCommand):
    help = "Cria/atualiza os grupos internos do portal com os poderes dos apps SCL."

    def handle(self, *args, **options):
        scl_content_types = [
            ContentType.objects.get_for_model(model)
            for app_config in apps.get_app_configs()
            if app_config.label in SCL_APPS
            for model in app_config.get_models()
        ]

        scl_permissions = list(
            Permission.objects.filter(content_type__in=scl_content_types)
        )

        for role, permission_prefixes in ROLE_PERMISSION_PREFIXES.items():
            group, created = Group.objects.get_or_create(name=role)

            filtered = [
                permission
                for permission in scl_permissions
                if any(permission.codename.startswith(prefix) for prefix in permission_prefixes)
            ]

            group.permissions.set(filtered)

            suffix = " (grupo criado)" if created else ""
            self.stdout.write(f"{role}: {len(filtered)} permissões SCL aplicadas{suffix}")

        self.stdout.write(self.style.SUCCESS("sync_roles concluído"))
