from django.urls import path

from financeiro.api.webhooks import processar_webhook

app_name = "payments"

urlpatterns = [
    path(
        "webhooks/<str:provedor>/<uuid:conta_public_id>/",
        processar_webhook,
        name="webhook",
    ),
]
