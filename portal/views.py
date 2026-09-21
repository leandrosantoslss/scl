from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponseNotAllowed
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from licencas.models import Cliente, ClienteSistema, Sistema


REMEMBER_ME_DURACAO = 60 * 60 * 24 * 14  # 14 dias


class RememberMeLoginView(auth_views.LoginView):
    """Login que estende a sessão quando 'Lembre de mim' está marcado."""

    template_name = "registration/login.html"
    form_class = AuthenticationForm

    def form_valid(self, form):
        resposta = super().form_valid(form)
        lembre = self.request.POST.get("remember_me") == "on"
        if lembre:
            self.request.session.set_expiry(REMEMBER_ME_DURACAO)
        else:
            self.request.session.set_expiry(0)
        return resposta


class LogoutPOSTView(auth_views.LogoutView):
    def get(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(["POST"])


@login_required
def home(request):
    context = {
        "clientes_total": Cliente.objects.count(),
        "sistemas_total": Sistema.objects.count(),
        "assinaturas_total": ClienteSistema.objects.count(),
    }
    return render(request, "portal/home.html", context)


class PasswordResetView(auth_views.PasswordResetView):
    success_url = reverse_lazy("password_reset_done")
    email_template_name = "registration/password_reset_email.html"
    subject_template_name = "registration/password_reset_subject.txt"


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    success_url = reverse_lazy("password_reset_complete")
