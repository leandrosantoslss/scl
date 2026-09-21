from app.admin_site import admin_site
from .models import Cliente, Sistema, AcessoMaquina, ClienteSistema

from django.contrib import admin  # noqa: F401, reexport for ModelAdmin classes


class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cnpjcpf', 'criado_em', 'ativo')
    search_fields = ('nome', 'cnpjcpf',)
    list_filter = ('nome', 'cnpjcpf', 'ativo',)


class SistemaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'criado_em', 'ativo')
    search_fields = ('nome',)
    list_filter = ('nome', 'ativo',)


class AcessoMaquinaAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'sistema', 'usuario', 'criado_em')
    search_fields = ('cliente', 'sistema')
    list_filter = ('cliente', 'sistema', 'usuario',)


class ClienteSistemaAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'sistema', 'ativo', 'criado_em')
    list_filter = ('ativo',)


admin_site.register(Cliente, ClienteAdmin)
admin_site.register(Sistema, SistemaAdmin)
admin_site.register(AcessoMaquina, AcessoMaquinaAdmin)
admin_site.register(ClienteSistema, ClienteSistemaAdmin)
