from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotAllowed
from django.shortcuts import render

from licencas.models import Cliente, ClienteSistema, Sistema


@login_required
def home(request):
    context = {
        "clientes_total": Cliente.objects.count(),
        "sistemas_total": Sistema.objects.count(),
        "assinaturas_total": ClienteSistema.objects.count(),
    }
    return render(request, "portal/home.html", context)


class LogoutPOSTView(auth_views.LogoutView):
    def get(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(["POST"])
